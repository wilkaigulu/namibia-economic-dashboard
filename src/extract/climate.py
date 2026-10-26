"""Download daily temperature and rainfall from NASA POWER for each region.

Changes from v1:
  * ten regional grid points instead of a single Windhoek point, which is what
    makes regional drought comparison and a Namibia map possible at all
  * record starts in 1981 so a WMO 1991-2020 baseline can be computed
  * explicit YYYYMMDD start/end (the API tolerates bare years, but undocumented)
  * retries, raises on failure, creates directories
  * the national reference point is still written to temperature.csv /
    rainfall.csv so nothing downstream of v1 breaks
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (
    CLIMATE_DIR,
    CLIMATE_REGIONS_DIR,
    CONFIG,
    FetchError,
    ensure_dirs,
    fetch_json,
    get_logger,
)

log = get_logger("extract.climate")

PARAMETERS = "T2M,T2M_MAX,PRECTOTCORR"
START = "19810101"
END = (dt.date.today() - dt.timedelta(days=7)).strftime("%Y%m%d")  # POWER lags ~a few days

FILL = -999.0  # POWER's missing-value sentinel


def load_regions() -> list[dict]:
    with open(CONFIG / "regions.json", encoding="utf-8") as fh:
        return json.load(fh)["regions"]


def fetch_point(region: dict, session: requests.Session) -> pd.DataFrame:
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters={PARAMETERS}"
        "&community=AG"
        f"&longitude={region['lon']}&latitude={region['lat']}"
        f"&start={START}&end={END}&format=JSON"
    )
    payload = fetch_json(url, session=session, timeout=180)

    try:
        params = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise FetchError(f"{region['slug']}: unexpected POWER response ({exc})") from exc

    df = pd.DataFrame({
        "date": pd.to_datetime(list(params["T2M"].keys()), format="%Y%m%d"),
        "t2m": list(params["T2M"].values()),
        "t2m_max": list(params.get("T2M_MAX", params["T2M"]).values()),
        "precip_mm": list(params["PRECTOTCORR"].values()),
    })

    # POWER encodes gaps as -999; leaving them in silently poisons every mean.
    for col in ("t2m", "t2m_max", "precip_mm"):
        df.loc[df[col] <= FILL, col] = pd.NA

    df["region"] = region["slug"]
    df["region_name"] = region["name"]
    df["zone"] = region.get("zone", "")
    return df.sort_values("date")


def main() -> int:
    ensure_dirs()
    regions = load_regions()
    log.info("fetching %s regional points, %s to %s", len(regions), START, END)

    frames: list[pd.DataFrame] = []
    failures: list[str] = []

    with requests.Session() as session:
        for region in regions:
            try:
                df = fetch_point(region, session)
            except FetchError as exc:
                log.error("%s", exc)
                failures.append(region["slug"])
                continue

            df.to_csv(CLIMATE_REGIONS_DIR / f"{region['slug']}_daily.csv", index=False)
            frames.append(df)
            log.info("%-14s %6d days  mean %.1f C  annual rain %.0f mm",
                     region["slug"], len(df), df["t2m"].mean(),
                     df["precip_mm"].sum() / max(df["date"].dt.year.nunique(), 1))

            if region.get("national_reference"):
                # Back-compatible single-point files, kept so that existing
                # Power BI queries pointing at these paths keep working.
                df[["date", "t2m"]].rename(columns={"t2m": "value"}).to_csv(
                    CLIMATE_DIR / "temperature.csv", index=False)
                df[["date", "precip_mm"]].rename(columns={"precip_mm": "value"}).to_csv(
                    CLIMATE_DIR / "rainfall.csv", index=False)

    if frames:
        pd.concat(frames, ignore_index=True).to_csv(
            CLIMATE_DIR / "climate_daily_all_regions.csv", index=False)

    if failures:
        log.error("FAILED regions: %s", ", ".join(failures))
        return 1

    log.info("climate extract complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
