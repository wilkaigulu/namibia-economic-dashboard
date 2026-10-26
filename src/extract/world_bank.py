"""Download World Bank indicators for Namibia.

Changes from v1:
  * fails loudly (raises) instead of `continue`-ing past an HTTP error, so a
    broken refresh cannot masquerade as a successful one
  * retries transient failures
  * end year is derived from today instead of being frozen at 2025
  * creates output directories
  * carries unit/category/label metadata through to dim_indicator
  * writes a tidy long-format CSV: date, value, indicator, unit, source
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CONFIG, WB_DIR, FetchError, ensure_dirs, fetch_json, get_logger

log = get_logger("extract.world_bank")

COUNTRY = "NAM"
START_YEAR = 1990
END_YEAR = dt.date.today().year


def load_indicators() -> dict:
    with open(CONFIG / "indicators.json", encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def fetch_indicator(key: str, meta: dict, session: requests.Session) -> pd.DataFrame:
    url = (
        f"https://api.worldbank.org/v2/country/{COUNTRY}"
        f"/indicator/{meta['code']}"
        f"?format=json&date={START_YEAR}:{END_YEAR}&per_page=500"
    )
    payload = fetch_json(url, session=session)

    # The API answers [{pagination}, [observations]] on success and
    # [{message:[...]}] when the indicator code is wrong.
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        raise FetchError(f"{key}: unexpected response for {meta['code']}: {payload!r:.200}")

    rows = [
        {"date": item["date"], "value": item["value"]}
        for item in payload[1]
        if item.get("value") is not None
    ]

    df = pd.DataFrame(rows)
    if df.empty:
        log.warning("%s returned no observations — check code %s", key, meta["code"])
        return df

    df["date"] = df["date"].astype(int)
    df = df.sort_values("date")
    df["indicator"] = key
    df["unit"] = meta.get("unit", "")
    df["source"] = "World Bank"
    return df[["date", "indicator", "value", "unit", "source"]]


def main() -> int:
    ensure_dirs()
    indicators = load_indicators()
    log.info("fetching %s indicators for %s (%s-%s)", len(indicators), COUNTRY, START_YEAR, END_YEAR)

    failures: list[str] = []
    empty: list[str] = []

    with requests.Session() as session:
        for key, meta in indicators.items():
            try:
                df = fetch_indicator(key, meta, session)
            except FetchError as exc:
                log.error("%s", exc)
                failures.append(key)
                continue

            if df.empty:
                empty.append(key)
                continue

            out = WB_DIR / f"{key.lower()}.csv"
            df.to_csv(out, index=False)
            log.info("%-20s %4d obs  %s-%s", key, len(df), df["date"].min(), df["date"].max())

    if empty:
        log.warning("no data returned for: %s", ", ".join(empty))

    if failures:
        # Partial success is still a failure: the dashboard would publish a
        # mix of fresh and stale series with no way to tell them apart.
        log.error("FAILED indicators: %s", ", ".join(failures))
        return 1

    log.info("World Bank extract complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
