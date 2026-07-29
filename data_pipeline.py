"""
Namibia Economic Dashboard — Data Pipeline
============================================

AUTO sources (World Bank API — runs automatically):
  - GDP growth (NY.GDP.MKTP.KD.ZG)
  - Unemployment (SL.UEM.TOTL.ZS)
  - Trade (% of GDP) (NE.TRD.GNFS.ZS)
  - FDI net inflows (BX.KLT.DINV.CD.WD)
  - Govt debt-to-GDP (GC.DOD.TOTL.GD.ZS) — patchy for Namibia

MANUAL sources (you update ~10 min/month):
  - inflation_manual.csv — from NSA NCPI Excel / BoN bulletins
  - repo_rate_manual.csv — from BoN MPC statements
  - trade_balance_manual.csv — from BoN quarterly bulletins
  - electricity_manual.csv — from NamPower annual report / IRENA
  - hydrogen_manual.csv — from NGH2P reports, news, your curation

Run: python data_pipeline.py
"""

import requests
import json
import csv
from pathlib import Path
from datetime import datetime

# ========== CONFIG ==========
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ========== WORLD BANK API FETCHER ==========

def fetch_world_bank(indicator, country="NAM", years=25):
    """
    Fetch data from World Bank API.
    Returns list of (year, value) tuples.
    """
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
    params = {
        "format": "json",
        "per_page": 500,
        "date": f"{datetime.now().year - years}:{datetime.now().year}"
    }
    try:
        print(f"  Fetching {indicator}...")
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        if len(data) < 2 or not data[1]:
            print(f"  ⚠️  No data returned for {indicator}")
            return []

        results = []
        for item in data[1]:
            year = item.get("date")
            value = item.get("value")
            if year and value is not None:
                results.append((int(year), float(value)))

        print(f"  ✓ {len(results)} records fetched")
        return sorted(results)

    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  Network error for {indicator}: {e}")
        return []
    except Exception as e:
        print(f"  ⚠️  Error processing {indicator}: {e}")
        return []

# ========== AUTO COLLECTION FROM WORLD BANK ==========

print("=" * 60)
print("NAMIBIA ECONOMIC DASHBOARD — DATA PIPELINE")
print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 1. GDP Growth (annual %)
print("\n[AUTO] 1/5 — GDP Growth...")
gdp = fetch_world_bank("NY.GDP.MKTP.KD.ZG")
if gdp:
    with open(DATA_DIR / "gdp_growth.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Year", "GDP_Growth_Pct", "Source"])
        for year, val in gdp:
            writer.writerow([year, round(val, 2), "World Bank API"])

# 2. Unemployment (ILO model)
print("\n[AUTO] 2/5 — Unemployment...")
unemp = fetch_world_bank("SL.UEM.TOTL.ZS")
if unemp:
    with open(DATA_DIR / "unemployment_wb.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Year", "Unemployment_Pct", "Source"])
        for year, val in unemp:
            writer.writerow([year, round(val, 2), "World Bank API (ILO model)"])

# 3. Trade (% of GDP)
print("\n[AUTO] 3/5 — Trade Balance (% GDP)...")
trade = fetch_world_bank("NE.TRD.GNFS.ZS")
if trade:
    with open(DATA_DIR / "trade_pct_gdp.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Year", "Trade_Balance_Pct_GDP", "Source"])
        for year, val in trade:
            writer.writerow([year, round(val, 2), "World Bank API"])

# 4. FDI net inflows
print("\n[AUTO] 4/5 — FDI Net Inflows...")
fdi = fetch_world_bank("BX.KLT.DINV.CD.WD")
if fdi:
    with open(DATA_DIR / "fdi_inflows.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Year", "FDI_Net_Inflows_USD_Million", "Source"])
        for year, val in fdi:
            writer.writerow([year, round(val / 1_000_000, 2), "World Bank API"])

# 5. Government debt-to-GDP (patchy for Namibia)
print("\n[AUTO] 5/5 — Government Debt-to-GDP...")
debt = fetch_world_bank("GC.DOD.TOTL.GD.ZS")
if debt:
    with open(DATA_DIR / "debt_wb.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Year", "Debt_to_GDP_Pct", "Source", "Note"])
        for year, val in debt:
            note = "WB data available" if val > 0 else "Missing for Namibia"
            writer.writerow([year, round(val, 2) if val else "", "World Bank API", note])
    print("  ⚠️  Note: Namibia debt data is often patchy in WB. Use manual override if needed.")

# ========== CHECK MANUAL FILES EXIST ==========

print("\n" + "=" * 60)
print("CHECKING MANUAL SOURCE FILES")
print("=" * 60)

manual_files = [
    "inflation_manual.csv",
    "repo_rate_manual.csv",
    "trade_balance_manual.csv",
    "electricity_manual.csv",
    "hydrogen_manual.csv"
]

for filename in manual_files:
    filepath = DATA_DIR / filename
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        print(f"  ✓ {filename} — {len(rows)-1} rows (YOU maintain this)")
    else:
        print(f"  ⚠️  {filename} — NOT FOUND")
        print(f"     → Create this file and add your manual data")

# ========== BUILD MASTER JSON ==========

print("\n" + "=" * 60)
print("BUILDING MASTER JSON")
print("=" * 60)

master = {
    "metadata": {
        "last_updated": datetime.now().isoformat(),
        "auto_sources": ["World Bank API"],
        "manual_sources": [
            "NSA NCPI (inflation_manual.csv)",
            "BoN MPC (repo_rate_manual.csv)",
            "BoN Quarterly Bulletin (trade_balance_manual.csv)",
            "NamPower / IRENA (electricity_manual.csv)",
            "NGH2P / News (hydrogen_manual.csv)"
        ],
        "next_manual_update": "Update inflation_manual.csv when NSA releases NCPI (~monthly)"
    }
}

# Load all CSVs into master
for csv_file in sorted(DATA_DIR.glob("*.csv")):
    key = csv_file.stem
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            master[key] = list(reader)
        print(f"  ✓ Loaded: {csv_file.name}")
    except Exception as e:
        print(f"  ⚠️  Error loading {csv_file.name}: {e}")

with open(DATA_DIR / "namibia_master.json", "w", encoding="utf-8") as f:
    json.dump(master, f, indent=2, ensure_ascii=False)

print(f"\n✅ MASTER JSON saved: {DATA_DIR / 'namibia_master.json'}")

print("\n" + "=" * 60)
print("PIPELINE COMPLETE")
print("=" * 60)
print("\nAUTO: World Bank API data refreshed")
print("MANUAL: Check _manual.csv files — update when new reports drop")
print("\nNext steps:")
print("  1. Update *_manual.csv files with latest BoN/NSA/NamPower data")
print("  2. Run: python data_pipeline.py")
print("  3. git add . && git commit -m 'Update data' && git push")
print("  4. Streamlit Cloud auto-redeploys")