"""Climate risk indicators: SPI drought, standardised heat, composite index.

WHY THIS WAS REWRITTEN
----------------------
The v1 index was `0.5*|rain_z| + 0.5*|temp_z|` computed on raw daily values
against the whole-record daily mean. Three things were wrong with it:

1. No seasonality. Namibia gets ~90% of its rain between December and March.
   A daily anomaly against the annual mean is therefore a measure of *what
   month it is*, not of drought. Every January scored as high risk and every
   July as low.
2. Absolute values. `|rain_z|` makes an unusually wet day score exactly like
   an unusually dry one. For a country whose main climate exposure is drought,
   above-normal rain is the opposite of risk.
3. Daily grain. A one-day rainfall deficit is weather. Drought is a
   multi-month accumulation deficit, which is what SPI measures.

WHAT IT DOES NOW
----------------
  * aggregates to monthly (precip sum, mean and max temperature)
  * fits SPI (Standardised Precipitation Index, McKee et al. 1993) per calendar
    month on 1/3/6/12-month accumulation windows, using a gamma distribution
    with a point mass at zero, fitted on a fixed baseline period
  * computes STI, a standardised temperature index, against the same baseline
  * builds a ONE-SIDED composite: only rainfall deficit and heat excess count
    as risk; a flood term is reported separately rather than folded in
  * emits a risk_band column ready for conditional formatting in Power BI

Outputs (all in data/automated/climate/):
  climate_monthly.csv       region x month panel with SPI/STI/composite
  climate_annual.csv        region x year rollup
  climate_risk_index.csv    national monthly series (replaces the orphan file)
  climate_risk_composite.csv national series, v1-compatible column names
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (
    CLIMATE_DIR,
    CLIMATE_REGIONS_DIR,
    CONFIG,
    ensure_dirs,
    get_logger,
)

log = get_logger("transform.climate_risk")

# Weights for the composite. Drought dominates because it is the channel
# through which Namibian climate shocks reach GDP, livestock and the fiscus.
W_DROUGHT = 0.65
W_HEAT = 0.35

MIN_BASELINE_YEARS = 20

RISK_BANDS = [
    (0.00, "Normal"),
    (0.80, "Watch"),
    (1.30, "Severe"),
    (2.00, "Extreme"),
]


# --------------------------------------------------------------------------
# Loading — works with the new regional files or the v1 national-only files
# --------------------------------------------------------------------------

def load_daily() -> pd.DataFrame:
    regional = sorted(CLIMATE_REGIONS_DIR.glob("*_daily.csv"))

    if regional:
        frames = [pd.read_csv(p, parse_dates=["date"]) for p in regional]
        df = pd.concat(frames, ignore_index=True)
        log.info("loaded %s regions, %s daily rows", df["region"].nunique(), f"{len(df):,}")
        return df

    # Fallback: the v1 layout, a single Windhoek point in two files with
    # YYYYMMDD integer dates.
    log.warning("no regional files found — falling back to national-only v1 inputs")
    rain = pd.read_csv(CLIMATE_DIR / "rainfall.csv")
    temp = pd.read_csv(CLIMATE_DIR / "temperature.csv")

    def _dates(s: pd.Series) -> pd.Series:
        s = s.astype(str).str.replace("-", "", regex=False).str.slice(0, 8)
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")

    rain["date"] = _dates(rain["date"])
    temp["date"] = _dates(temp["date"])

    df = (
        rain.rename(columns={"value": "precip_mm"})[["date", "precip_mm"]]
        .merge(temp.rename(columns={"value": "t2m"})[["date", "t2m"]], on="date", how="outer")
        .sort_values("date")
    )
    df["t2m_max"] = df["t2m"]
    df["region"] = "khomas"
    df["region_name"] = "Khomas (Windhoek)"
    df["zone"] = "Central Highlands"

    for col in ("precip_mm", "t2m", "t2m_max"):
        df.loc[df[col] <= -999.0, col] = np.nan

    return df


def to_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    daily = daily.dropna(subset=["date"]).copy()
    daily["month_start"] = daily["date"].values.astype("datetime64[M]")

    monthly = (
        daily.groupby(["region", "region_name", "zone", "month_start"], as_index=False)
        .agg(
            precip_mm=("precip_mm", "sum"),
            t2m=("t2m", "mean"),
            t2m_max=("t2m_max", "mean"),
            days=("date", "nunique"),
            hot_days_35=("t2m_max", lambda s: int((s >= 35).sum())),
            rain_days=("precip_mm", lambda s: int((s >= 1.0).sum())),
        )
    )

    # Drop partial months at the end of the record so the last point is not a
    # spurious low-rainfall month that reads as instant drought.
    monthly = monthly[monthly["days"] >= 27].copy()

    monthly = monthly.rename(columns={"month_start": "date"})
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month
    return monthly.sort_values(["region", "date"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# SPI
# --------------------------------------------------------------------------

def _spi_from_accumulation(acc: pd.Series, in_baseline: pd.Series) -> pd.Series:
    """Gamma-fit SPI for one calendar month at one accumulation window.

    Zero-rainfall months are handled with the standard mixed distribution:
    P(X <= x) = q + (1-q) * G(x), where q is the baseline probability of zero.
    """
    out = pd.Series(np.nan, index=acc.index, dtype=float)

    base = acc[in_baseline].dropna()
    if len(base) < 10:
        base = acc.dropna()
    if len(base) < 8:
        return out

    n_zero = int((base <= 0).sum())
    q = n_zero / len(base)
    positive = base[base > 0]

    if len(positive) < 5 or positive.nunique() < 3:
        return out

    try:
        shape, loc, scale = stats.gamma.fit(positive, floc=0)
    except Exception:  # noqa: BLE001 - degenerate sample, leave as NaN
        return out

    vals = acc.astype(float)
    cdf = np.where(
        vals <= 0,
        q,
        q + (1 - q) * stats.gamma.cdf(np.clip(vals, 1e-9, None), shape, loc=loc, scale=scale),
    )
    cdf = np.clip(cdf, 1e-6, 1 - 1e-6)
    out.loc[:] = stats.norm.ppf(cdf)
    out[vals.isna()] = np.nan
    return out


def add_spi(monthly: pd.DataFrame, baseline: tuple[int, int], windows=(1, 3, 6, 12)) -> pd.DataFrame:
    lo, hi = baseline
    monthly = monthly.copy()

    for w in windows:
        col = f"spi_{w}"
        monthly[col] = np.nan

        for _region, grp in monthly.groupby("region", sort=False):
            grp = grp.sort_values("date")
            acc = grp["precip_mm"].rolling(w, min_periods=w).sum()
            in_base = grp["year"].between(lo, hi)

            # SPI must be fitted separately per calendar month: a 3-month
            # accumulation ending in February is a different distribution
            # from one ending in August.
            for m in range(1, 13):
                mask = grp["month"] == m
                if mask.sum() < 8:
                    continue
                spi = _spi_from_accumulation(acc[mask], in_base[mask])
                monthly.loc[spi.index, col] = spi.values

    return monthly


# --------------------------------------------------------------------------
# Temperature + composite
# --------------------------------------------------------------------------

def add_temperature_index(monthly: pd.DataFrame, baseline: tuple[int, int]) -> pd.DataFrame:
    lo, hi = baseline
    monthly = monthly.copy()
    base = monthly[monthly["year"].between(lo, hi)]

    if base.empty:
        base = monthly

    clim = (
        base.groupby(["region", "month"], as_index=False)
        .agg(t2m_norm=("t2m", "mean"), t2m_sd=("t2m", "std"),
             tmax_norm=("t2m_max", "mean"))
    )

    monthly = monthly.merge(clim, on=["region", "month"], how="left")
    monthly["temp_anomaly_c"] = monthly["t2m"] - monthly["t2m_norm"]
    monthly["tmax_anomaly_c"] = monthly["t2m_max"] - monthly["tmax_norm"]
    monthly["sti"] = monthly["temp_anomaly_c"] / monthly["t2m_sd"].replace(0, np.nan)

    # Rainfall anomaly in mm and in % of normal — the units a non-technical
    # reader actually understands, alongside the z-score ones.
    rain_clim = (
        base.groupby(["region", "month"], as_index=False)
        .agg(precip_norm=("precip_mm", "mean"))
    )
    monthly = monthly.merge(rain_clim, on=["region", "month"], how="left")
    monthly["rain_anomaly_mm"] = monthly["precip_mm"] - monthly["precip_norm"]
    monthly["rain_pct_of_normal"] = np.where(
        monthly["precip_norm"] > 0,
        100 * monthly["precip_mm"] / monthly["precip_norm"],
        np.nan,
    )
    return monthly


def add_composite(monthly: pd.DataFrame) -> pd.DataFrame:
    monthly = monthly.copy()

    # One-sided terms: only the harmful tail is risk.
    monthly["drought_score"] = (-monthly["spi_12"]).clip(lower=0)
    monthly["heat_score"] = monthly["sti"].clip(lower=0)
    monthly["flood_score"] = monthly["spi_3"].clip(lower=0)  # reported, not summed

    monthly["climate_risk_index"] = (
        W_DROUGHT * monthly["drought_score"] + W_HEAT * monthly["heat_score"]
    )

    # 0-100 version for gauges and card visuals. 3.0 in z-units is about as
    # extreme as this index gets, so it anchors the top of the scale.
    monthly["climate_risk_0_100"] = (100 * monthly["climate_risk_index"] / 3.0).clip(0, 100)

    def band(x: float) -> str:
        if pd.isna(x):
            return "No data"
        label = RISK_BANDS[0][1]
        for threshold, name in RISK_BANDS:
            if x >= threshold:
                label = name
        return label

    monthly["risk_band"] = monthly["climate_risk_index"].map(band)
    return monthly


# --------------------------------------------------------------------------

def main() -> int:
    ensure_dirs()

    with open(CONFIG / "regions.json", encoding="utf-8") as fh:
        cfg = json.load(fh)["baseline"]
    baseline = (cfg["start_year"], cfg["end_year"])

    daily = load_daily()
    monthly = to_monthly(daily)

    span = monthly["year"].max() - monthly["year"].min() + 1
    covered = monthly["year"].between(*baseline).groupby(monthly["region"]).sum().max() / 12
    if covered < MIN_BASELINE_YEARS:
        log.warning(
            "record covers only ~%.0f years of the %s-%s baseline; falling back to the "
            "full %s-year record as the reference period. Re-run the climate extract "
            "from 1981 for a proper WMO normal.",
            covered, *baseline, span,
        )
        baseline = (int(monthly["year"].min()), int(monthly["year"].max()))

    monthly = add_spi(monthly, baseline)
    monthly = add_temperature_index(monthly, baseline)
    monthly = add_composite(monthly)
    monthly["baseline_period"] = f"{baseline[0]}-{baseline[1]}"

    cols = [
        "date", "year", "month", "region", "region_name", "zone",
        "precip_mm", "precip_norm", "rain_anomaly_mm", "rain_pct_of_normal",
        "t2m", "t2m_norm", "temp_anomaly_c", "t2m_max", "tmax_anomaly_c",
        "hot_days_35", "rain_days",
        "spi_1", "spi_3", "spi_6", "spi_12", "sti",
        "drought_score", "heat_score", "flood_score",
        "climate_risk_index", "climate_risk_0_100", "risk_band",
        "baseline_period",
    ]
    monthly = monthly[cols]
    monthly.to_csv(CLIMATE_DIR / "climate_monthly.csv", index=False)

    annual = (
        monthly.groupby(["region", "region_name", "zone", "year"], as_index=False)
        .agg(
            precip_mm=("precip_mm", "sum"),
            precip_norm=("precip_norm", "sum"),
            t2m=("t2m", "mean"),
            temp_anomaly_c=("temp_anomaly_c", "mean"),
            hot_days_35=("hot_days_35", "sum"),
            spi_12_year_end=("spi_12", "last"),
            drought_score=("drought_score", "max"),
            climate_risk_index=("climate_risk_index", "mean"),
            climate_risk_peak=("climate_risk_index", "max"),
        )
    )
    annual["rain_pct_of_normal"] = np.where(
        annual["precip_norm"] > 0, 100 * annual["precip_mm"] / annual["precip_norm"], np.nan)
    annual.to_csv(CLIMATE_DIR / "climate_annual.csv", index=False)

    # National series = unweighted mean across regions (swap in a
    # population- or GDP-weighted mean once you have regional weights).
    national = (
        monthly.groupby("date", as_index=False)
        .agg(
            precip_mm=("precip_mm", "mean"),
            rain_anomaly_mm=("rain_anomaly_mm", "mean"),
            rain_pct_of_normal=("rain_pct_of_normal", "mean"),
            t2m=("t2m", "mean"),
            temp_anomaly_c=("temp_anomaly_c", "mean"),
            spi_3=("spi_3", "mean"),
            spi_12=("spi_12", "mean"),
            sti=("sti", "mean"),
            drought_score=("drought_score", "mean"),
            heat_score=("heat_score", "mean"),
            climate_risk_index=("climate_risk_index", "mean"),
            regions_in_drought=("risk_band", lambda s: int((s.isin(["Severe", "Extreme"])).sum())),
        )
    )
    national["climate_risk_0_100"] = (100 * national["climate_risk_index"] / 3.0).clip(0, 100)
    national["region"] = "NATIONAL"
    national.to_csv(CLIMATE_DIR / "climate_risk_index.csv", index=False)
    national.to_csv(CLIMATE_DIR / "climate_risk_composite.csv", index=False)

    latest = national.dropna(subset=["climate_risk_index"]).tail(1)
    if not latest.empty:
        row = latest.iloc[0]
        log.info(
            "latest %s: risk %.2f, SPI-12 %.2f, temp anomaly %+.2f C",
            row["date"].date(), row["climate_risk_index"], row["spi_12"], row["temp_anomaly_c"],
        )

    log.info("wrote %s monthly region-months, %s annual rows", f"{len(monthly):,}", len(annual))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
