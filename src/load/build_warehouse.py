"""Build the star schema the Power BI model loads.

Changes from v1:
  * every series now carries unit, frequency, direction and is_forecast.
    Without a unit column, `value` mixed percent, N$ billion, USD and raw
    person-counts in one field, so any card or shared axis was meaningless.
    Without is_forecast, the IMF projections through 2029 in debt_to_gdp.csv
    plotted as if they were actuals.
  * raw DAILY climate is no longer loaded into fact_indicator. It was 38,000 of
    the table's 38,200 rows, which crushed Power BI performance and made every
    time-intelligence measure fight two different grains. The climate panel
    lives in fact_climate_monthly at region x month grain instead.
  * emits dim_indicator, dim_date and dim_region so the model can be a proper
    star instead of one flat table with no lookups.
  * declarative source registry instead of 20 repeated add_indicator() calls.
  * paths anchored to the repo root; output directories created.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (
    CLIMATE_DIR,
    CONFIG,
    CURATED_DIR,
    WAREHOUSE_DIR,
    WB_DIR,
    ensure_dirs,
    get_logger,
)

log = get_logger("load.build_warehouse")

CURRENT_YEAR = dt.date.today().year

# --------------------------------------------------------------------------
# Indicator registry
# --------------------------------------------------------------------------
# direction: how a reader should read an increase.
#   "up_good"   green when rising   (GDP growth, renewable share)
#   "up_bad"    red when rising     (inflation, debt, unemployment, risk)
#   "neutral"   no colour judgement (population, trade openness)

CURATED_SOURCES = [
    # file, date_col, value_col, indicator, label, unit, category, source, direction, benchmark
    ("debt_to_gdp.csv", "Year", "Debt_to_GDP_Pct", "DEBT_GDP",
     "Debt-to-GDP", "percent_gdp", "Finance", "Ministry of Finance / IMF", "up_bad", 60.0),
    ("debt_to_gdp.csv", "Year", "Total_Debt_NS_Billion", "TOTAL_DEBT",
     "Total public debt", "nad_billion", "Finance", "Ministry of Finance / IMF", "up_bad", None),
    ("debt_to_gdp.csv", "Year", "Fiscal_Deficit_Pct", "FISCAL_DEFICIT",
     "Fiscal deficit", "percent_gdp", "Finance", "Ministry of Finance / IMF", "up_bad", 3.0),
    ("debt_to_gdp.csv", "Year", "Interest_Payments_NS_Billion", "INTEREST_PAYMENTS",
     "Interest payments", "nad_billion", "Finance", "Ministry of Finance / IMF", "up_bad", None),

    ("inflation_history.csv", "Year", "Inflation_Rate_Pct", "INFLATION",
     "Inflation rate", "percent", "Economy", "Bank of Namibia", "up_bad", 4.5),

    ("unemployment.csv", "Survey_Year", "Strict_Unemployment_Pct", "UNEMPLOYMENT_STRICT",
     "Unemployment (strict)", "percent", "Labour", "NSA Labour Force Survey", "up_bad", None),
    ("unemployment.csv", "Survey_Year", "Broad_Unemployment_Pct", "UNEMPLOYMENT_BROAD",
     "Unemployment (broad)", "percent", "Labour", "NSA Labour Force Survey", "up_bad", None),
    ("unemployment.csv", "Survey_Year", "Youth_Unemployment_Est_Pct", "UNEMPLOYMENT_YOUTH",
     "Youth unemployment (est.)", "percent", "Labour", "NSA Labour Force Survey", "up_bad", None),

    ("trade_balance.csv", "Year", "Exports_NS_Million", "EXPORTS",
     "Merchandise exports", "nad_million", "Trade", "NSA", "up_good", None),
    ("trade_balance.csv", "Year", "Imports_NS_Million", "IMPORTS",
     "Merchandise imports", "nad_million", "Trade", "NSA", "neutral", None),
    ("trade_balance.csv", "Year", "Balance_NS_Million", "TRADE_BALANCE",
     "Trade balance", "nad_million", "Trade", "NSA", "up_good", 0.0),
]

# Rows at or beyond these years in these files are projections, not outturns.
FORECAST_FROM = {
    "DEBT_GDP": 2027,
    "TOTAL_DEBT": 2027,
    "FISCAL_DEFICIT": 2027,
    "INTEREST_PAYMENTS": 2027,
    "INFLATION": 2026,
}

records: list[pd.DataFrame] = []
dim_rows: list[dict] = []


def add(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    *,
    indicator: str,
    label: str,
    unit: str,
    category: str,
    source: str,
    frequency: str,
    direction: str = "neutral",
    benchmark: float | None = None,
    description: str = "",
) -> None:
    if date_col not in df.columns or value_col not in df.columns:
        log.warning("skipping %s: missing column %s/%s", indicator, date_col, value_col)
        return

    temp = pd.DataFrame({
        "date": df[date_col],
        "indicator": indicator,
        "value": pd.to_numeric(df[value_col], errors="coerce"),
    })
    temp["unit"] = unit
    temp["frequency"] = frequency
    temp["category"] = category
    temp["source"] = source
    records.append(temp)

    dim_rows.append({
        "indicator": indicator,
        "label": label,
        "category": category,
        "unit": unit,
        "frequency": frequency,
        "source": source,
        "direction": direction,
        "benchmark": benchmark,
        "description": description,
    })


def standardize_date(series: pd.Series) -> pd.Series:
    """Accept bare years, YYYYMMDD, and ISO dates in one column."""
    s = series.astype(str).str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    annual = s.str.fullmatch(r"\d{4}")
    out.loc[annual] = pd.to_datetime(s.loc[annual] + "-01-01", errors="coerce")

    compact = ~annual & s.str.fullmatch(r"\d{8}")
    out.loc[compact] = pd.to_datetime(s.loc[compact], format="%Y%m%d", errors="coerce")

    rest = ~annual & ~compact
    out.loc[rest] = pd.to_datetime(s.loc[rest], errors="coerce", format="mixed")
    return out


# --------------------------------------------------------------------------
# World Bank
# --------------------------------------------------------------------------

def load_world_bank() -> None:
    with open(CONFIG / "indicators.json", encoding="utf-8") as fh:
        meta_all = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}

    directions = {
        "percent": "neutral", "percent_gdp": "neutral",
        "usd": "up_good", "persons": "neutral", "months": "up_good",
        "kgoe": "neutral", "tco2e": "up_bad",
    }
    overrides = {
        "GDP_GROWTH": "up_good", "GDP_PER_CAPITA": "up_good",
        "INFLATION_WB": "up_bad", "UNEMPLOYMENT_WB": "up_bad",
        "YOUTH_UNEMP_WB": "up_bad", "DEBT_GDP_WB": "up_bad",
        "FDI": "up_good", "RENEWABLE_SHARE": "up_good",
        "RENEWABLE_ELEC": "up_good", "ELECTRICITY_ACCESS": "up_good",
        "CO2_PER_CAPITA": "up_bad", "WATER_STRESS": "up_bad",
        "EXPORTS_GDP": "up_good", "RESERVES_MONTHS": "up_good",
    }

    # Filenames written by the v1 extractor, before the keys were renamed.
    # Lets an offline rebuild use CSVs already committed to the repo.
    legacy = {
        "INFLATION_WB": "inflation.csv",
        "UNEMPLOYMENT_WB": "unemployment.csv",
        "DEBT_GDP_WB": "debt_gdp.csv",
    }

    found = 0
    for key, meta in meta_all.items():
        path = WB_DIR / f"{key.lower()}.csv"
        if not path.exists() and key in legacy:
            path = WB_DIR / legacy[key]
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "date" not in df.columns or "value" not in df.columns:
            log.warning("%s has unexpected columns: %s", path.name, list(df.columns))
            continue

        add(
            df, "date", "value",
            indicator=key,
            label=meta.get("label", key),
            unit=meta.get("unit", ""),
            category=meta.get("category", "Economy"),
            source="World Bank",
            frequency="annual",
            direction=overrides.get(key, directions.get(meta.get("unit", ""), "neutral")),
            description=f"World Bank indicator {meta['code']}",
        )
        found += 1

    log.info("World Bank: %s series loaded", found)


# --------------------------------------------------------------------------
# Curated national statistics
# --------------------------------------------------------------------------

def load_curated() -> None:
    cache: dict[str, pd.DataFrame] = {}

    for (file, date_col, value_col, indicator, label, unit,
         category, source, direction, benchmark) in CURATED_SOURCES:
        path = CURATED_DIR / file
        if not path.exists():
            log.warning("missing curated file %s", file)
            continue
        if file not in cache:
            cache[file] = pd.read_csv(path)

        add(
            cache[file], date_col, value_col,
            indicator=indicator, label=label, unit=unit, category=category,
            source=source, frequency="annual", direction=direction,
            benchmark=benchmark,
        )

    log.info("curated: %s series loaded", len(CURATED_SOURCES))


# --------------------------------------------------------------------------
# Climate — monthly only in the fact table
# --------------------------------------------------------------------------

def load_climate() -> pd.DataFrame | None:
    monthly_path = CLIMATE_DIR / "climate_monthly.csv"
    national_path = CLIMATE_DIR / "climate_risk_index.csv"

    if not national_path.exists():
        log.warning("no climate_risk_index.csv — run src/transform/climate_risk.py first")
        return None

    nat = pd.read_csv(national_path, parse_dates=["date"])

    climate_series = [
        ("climate_risk_index", "CLIMATE_RISK_INDEX", "Climate risk index",
         "z_score", "up_bad", 1.3),
        ("drought_score", "DROUGHT_SCORE", "Drought severity (-SPI-12)",
         "z_score", "up_bad", 1.3),
        ("spi_12", "SPI_12", "SPI-12 (12-month rainfall)", "z_score", "up_good", -1.0),
        ("spi_3", "SPI_3", "SPI-3 (3-month rainfall)", "z_score", "up_good", -1.0),
        ("temp_anomaly_c", "TEMP_ANOMALY", "Temperature anomaly", "celsius", "up_bad", None),
        ("rain_pct_of_normal", "RAIN_PCT_NORMAL", "Rainfall, % of normal",
         "percent", "up_good", 100.0),
        ("precip_mm", "RAINFALL_MONTHLY", "Monthly rainfall", "mm", "up_good", None),
        ("t2m", "TEMPERATURE", "Mean temperature", "celsius", "neutral", None),
    ]

    for col, indicator, label, unit, direction, benchmark in climate_series:
        if col not in nat.columns:
            continue
        add(
            nat, "date", col,
            indicator=indicator, label=label, unit=unit, category="Climate",
            source="NASA POWER / derived", frequency="monthly",
            direction=direction, benchmark=benchmark,
            description="National mean across regional grid points",
        )

    if monthly_path.exists():
        return pd.read_csv(monthly_path, parse_dates=["date"])
    return None


# --------------------------------------------------------------------------
# Dimensions
# --------------------------------------------------------------------------

def build_dim_date(lo: pd.Timestamp, hi: pd.Timestamp) -> pd.DataFrame:
    dates = pd.date_range(f"{lo.year}-01-01", f"{hi.year}-12-31", freq="MS")
    d = pd.DataFrame({"date": dates})
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    d["quarter"] = d["date"].dt.quarter
    d["month_name"] = d["date"].dt.strftime("%b")
    d["month_short"] = d["date"].dt.strftime("%Y-%m")
    d["quarter_label"] = d["year"].astype(str) + "-Q" + d["quarter"].astype(str)
    # Namibian fiscal year runs 1 April to 31 March.
    d["fiscal_year"] = d["year"].where(d["month"] >= 4, d["year"] - 1)
    d["fiscal_year_label"] = (
        "FY" + d["fiscal_year"].astype(str).str[-2:]
        + "/" + (d["fiscal_year"] + 1).astype(str).str[-2:]
    )
    # Rainfall season runs Oct-Sep; Namibian drought years are named by the
    # season, not the calendar year, so a calendar axis splits every drought.
    d["rain_season"] = d["year"].where(d["month"] >= 10, d["year"] - 1)
    d["rain_season_label"] = (
        d["rain_season"].astype(str) + "/" + (d["rain_season"] + 1).astype(str).str[-2:]
    )
    d["is_future"] = d["year"] > CURRENT_YEAR
    return d


def build_dim_region() -> pd.DataFrame:
    with open(CONFIG / "regions.json", encoding="utf-8") as fh:
        regions = json.load(fh)["regions"]
    df = pd.DataFrame(regions)
    df["national_reference"] = df.get("national_reference", False)
    return df.fillna({"note": "", "national_reference": False})


# --------------------------------------------------------------------------

def main() -> int:
    ensure_dirs()

    load_world_bank()
    load_curated()
    climate_panel = load_climate()

    if not records:
        log.error("no records collected — nothing to build")
        return 1

    fact = pd.concat(records, ignore_index=True)
    fact["date"] = standardize_date(fact["date"])
    fact = fact.dropna(subset=["date", "value"])

    fact["year"] = fact["date"].dt.year
    fact["month"] = fact["date"].dt.month
    fact["quarter"] = fact["date"].dt.quarter

    fact["is_forecast"] = False
    for indicator, from_year in FORECAST_FROM.items():
        mask = (fact["indicator"] == indicator) & (fact["year"] >= from_year)
        fact.loc[mask, "is_forecast"] = True

    before = len(fact)
    fact = fact.drop_duplicates(subset=["indicator", "date"], keep="last")
    if before != len(fact):
        log.warning("dropped %s duplicate indicator/date rows", before - len(fact))

    fact = fact.sort_values(["indicator", "date"]).reset_index(drop=True)
    fact = fact[[
        "date", "year", "month", "quarter", "indicator", "value",
        "unit", "frequency", "category", "source", "is_forecast",
    ]]

    dim_indicator = (
        pd.DataFrame(dim_rows).drop_duplicates(subset=["indicator"], keep="first")
        .sort_values(["category", "indicator"])
        .reset_index(drop=True)
    )

    dim_date = build_dim_date(fact["date"].min(), fact["date"].max())
    dim_region = build_dim_region()

    outputs = {
        "fact_indicator": fact,
        "dim_indicator": dim_indicator,
        "dim_date": dim_date,
        "dim_region": dim_region,
    }
    if climate_panel is not None:
        outputs["fact_climate_monthly"] = climate_panel

    for name, df in outputs.items():
        df.to_csv(WAREHOUSE_DIR / f"{name}.csv", index=False)
        try:
            df.to_parquet(WAREHOUSE_DIR / f"{name}.parquet", index=False)
        except Exception as exc:  # noqa: BLE001 - parquet is a convenience, CSV is the contract
            log.warning("parquet write failed for %s (%s); CSV written", name, exc)
        log.info("%-22s %7s rows x %2s cols", name, f"{len(df):,}", len(df.columns))

    log.info(
        "fact_indicator: %s series, %s to %s",
        fact["indicator"].nunique(), fact["date"].min().date(), fact["date"].max().date(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
