"""Data quality gate.

v1 was three asserts (non-empty, has date, has value). That passes on almost
any garbage: an all-null value column, a duplicated series, 1970 dates, a
quarterly refresh that quietly fetched nothing new.

This version runs named checks, prints a report, and exits non-zero on any
ERROR so CI goes red instead of committing bad data. WARN findings are
printed but do not fail the run.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import WAREHOUSE_DIR, get_logger

log = get_logger("validate")

MAX_STALENESS_DAYS = 420  # annual data plus a grace period

# Plausible ranges. A value outside these is almost certainly a units or
# parsing bug, not a real observation.
RANGES = {
    "GDP_GROWTH": (-20, 20),
    "GDP_PER_CAPITA": (500, 20_000),
    "INFLATION": (-5, 60),
    "INFLATION_WB": (-5, 60),
    "UNEMPLOYMENT_STRICT": (5, 70),
    "UNEMPLOYMENT_BROAD": (5, 80),
    "UNEMPLOYMENT_WB": (5, 70),
    "DEBT_GDP": (10, 150),
    "FISCAL_DEFICIT": (-10, 20),
    "TOTAL_DEBT": (10, 600),
    "POPULATION": (1_000_000, 6_000_000),
    "RENEWABLE_SHARE": (0, 100),
    "RENEWABLE_ELEC": (0, 100),
    "ELECTRICITY_ACCESS": (0, 100),
    # Wide on purpose. In an arid dry-season month the 1991-2020 normal can be
    # 0.2 mm, so 5 mm of rain is legitimately 2,500% of normal. Use
    # rain_anomaly_mm or SPI for dry-season comparisons; % of normal is only
    # meaningful inside the Dec-Mar rainfall season.
    "RAIN_PCT_NORMAL": (0, 5000),
    "SPI_12": (-4, 4),
    "SPI_3": (-4, 4),
    "CLIMATE_RISK_INDEX": (0, 5),
    "DROUGHT_SCORE": (0, 5),
    "TEMP_ANOMALY": (-8, 8),
    "TEMPERATURE": (0, 45),
    "RAINFALL_MONTHLY": (0, 800),
}

findings: list[tuple[str, str, str]] = []


def record(level: str, check: str, message: str) -> None:
    findings.append((level, check, message))


def main() -> int:
    fact_path = WAREHOUSE_DIR / "fact_indicator.csv"
    if not fact_path.exists():
        log.error("fact_indicator.csv does not exist — build step did not run")
        return 1

    fact = pd.read_csv(fact_path, parse_dates=["date"])

    # ---- structure -------------------------------------------------------
    required = {"date", "indicator", "value", "unit", "frequency",
                "category", "source", "is_forecast", "year"}
    missing = required - set(fact.columns)
    if missing:
        record("ERROR", "schema", f"missing columns: {sorted(missing)}")

    if fact.empty:
        record("ERROR", "non_empty", "fact table has zero rows")
        _report()
        return 1

    # ---- nulls -----------------------------------------------------------
    for col in ("date", "indicator", "value"):
        if col in fact.columns and fact[col].isna().any():
            record("ERROR", "nulls", f"{fact[col].isna().sum()} nulls in '{col}'")

    if "unit" in fact.columns:
        blank = fact["unit"].isna() | (fact["unit"].astype(str).str.strip() == "")
        if blank.any():
            bad = sorted(fact.loc[blank, "indicator"].unique())
            record("ERROR", "units", f"indicators with no unit: {bad}")

    # ---- duplicates ------------------------------------------------------
    dupes = fact.duplicated(subset=["indicator", "date"]).sum()
    if dupes:
        record("ERROR", "duplicates", f"{dupes} duplicate indicator/date pairs")

    # ---- dates -----------------------------------------------------------
    lo = fact["date"].min()
    if lo < pd.Timestamp("1960-01-01"):
        record("ERROR", "date_floor", f"earliest date {lo.date()} looks like a parsing bug")

    actuals = fact[~fact["is_forecast"].astype(bool)] if "is_forecast" in fact else fact
    if not actuals.empty:
        latest_actual = actuals["date"].max()
        age = (dt.date.today() - latest_actual.date()).days
        if age > MAX_STALENESS_DAYS:
            record("WARN", "freshness",
                   f"newest non-forecast observation is {latest_actual.date()} ({age} days old)")

    future_actuals = actuals[actuals["year"] > dt.date.today().year]
    if not future_actuals.empty:
        bad = sorted(future_actuals["indicator"].unique())
        record("ERROR", "forecast_flag",
               f"future-dated rows not flagged as forecast: {bad} — add them to FORECAST_FROM")

    # ---- ranges ----------------------------------------------------------
    for indicator, (low, high) in RANGES.items():
        sub = fact[fact["indicator"] == indicator]
        if sub.empty:
            continue
        out = sub[(sub["value"] < low) | (sub["value"] > high)]
        if not out.empty:
            record("ERROR", "range",
                   f"{indicator}: {len(out)} values outside [{low}, {high}] "
                   f"(min {sub['value'].min():.2f}, max {sub['value'].max():.2f})")

    # ---- series health ---------------------------------------------------
    counts = fact.groupby("indicator").size()
    thin = counts[counts < 3]
    if not thin.empty:
        record("WARN", "thin_series",
               f"fewer than 3 observations: {dict(thin)} — a line chart of these is a dot")

    flat = (
        fact.groupby("indicator")["value"].nunique()
        .loc[lambda s: s == 1]
    )
    if not flat.empty:
        record("WARN", "constant_series",
               f"constant across the whole record: {sorted(flat.index)}")

    # ---- dimension integrity --------------------------------------------
    dim_path = WAREHOUSE_DIR / "dim_indicator.csv"
    if dim_path.exists():
        dim = pd.read_csv(dim_path)
        orphans = set(fact["indicator"]) - set(dim["indicator"])
        if orphans:
            record("ERROR", "dim_coverage",
                   f"indicators in the fact table with no dim_indicator row: {sorted(orphans)}")
        if dim["indicator"].duplicated().any():
            record("ERROR", "dim_unique", "dim_indicator has duplicate keys")
    else:
        record("ERROR", "dim_missing", "dim_indicator.csv not written")

    # ---- row-count regression -------------------------------------------
    stamp = WAREHOUSE_DIR / ".last_row_count"
    if stamp.exists():
        try:
            previous = int(stamp.read_text().strip())
            if len(fact) < previous * 0.9:
                record("ERROR", "row_regression",
                       f"row count fell from {previous:,} to {len(fact):,} (>10% loss)")
        except ValueError:
            pass
    stamp.write_text(str(len(fact)))

    return _report()


def _report() -> int:
    errors = [f for f in findings if f[0] == "ERROR"]
    warns = [f for f in findings if f[0] == "WARN"]

    for level, check, message in findings:
        (log.error if level == "ERROR" else log.warning)("[%s] %s", check, message)

    if errors:
        log.error("validation FAILED: %s error(s), %s warning(s)", len(errors), len(warns))
        return 1

    log.info("validation passed (%s warning(s))", len(warns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
