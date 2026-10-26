# System architecture

## Flow

```
                 ┌────────────────────┐
                 │  World Bank API    │  22 indicators, annual, 1990→
                 └─────────┬──────────┘
                           │  src/extract/world_bank.py
                 ┌─────────▼──────────┐
                 │  NASA POWER API    │  10 regional points, daily, 1981→
                 └─────────┬──────────┘
                           │  src/extract/climate.py
        ┌──────────────────▼──────────────────┐
        │  data/automated/                    │
        │    world_bank/*.csv                 │
        │    climate/regions/*_daily.csv      │
        └──────────────────┬──────────────────┘
                           │  src/transform/climate_risk.py
                           │    → monthly aggregation
                           │    → SPI-1/3/6/12 (gamma, per calendar month)
                           │    → STI, one-sided composite, risk bands
        ┌──────────────────▼──────────────────┐
        │  data/curated/      (NSA, BoN, MoF) │
        │  data/dimension/    (energy, H2)    │
        └──────────────────┬──────────────────┘
                           │  src/load/build_warehouse.py
        ┌──────────────────▼──────────────────┐
        │  data/warehouse/  (CSV + Parquet)   │
        │    fact_indicator                   │
        │    fact_climate_monthly             │
        │    dim_indicator · dim_date         │
        │    dim_region                       │
        └──────────────────┬──────────────────┘
                           │  src/validate/validate_data.py
                           │    schema · nulls · units · duplicates
                           │    ranges · freshness · forecast flags
                           │    dim coverage · row-count regression
                           ▼
                    Power BI model
```

## Design decisions

**Fail-closed orchestration.** `pipeline.py` runs each step with `check=True`. A failure
aborts the run, so nothing downstream executes and the warehouse retains its last good
build. The CI job only commits on success.

**Star schema, not one flat table.** `fact_indicator` holds measures; `dim_indicator`,
`dim_date` and `dim_region` hold attributes. This is what lets a single `Latest Value`
measure serve all 27 series instead of 27 hand-written measures.

**Monthly, not daily, climate in the fact table.** Daily climate was 38,000 of
fact_indicator's 38,200 rows in v1 — it dominated the model, slowed every visual, and
forced time-intelligence measures to straddle two grains. Daily data is still extracted
and kept on disk; the warehouse carries the monthly panel.

**Fixed climatological baseline.** Anomalies are measured against a fixed window
(WMO 1991–2020 where available), not a moving full-record mean. With a moving mean the
warming trend is partly absorbed into the baseline and the index understates it.

**Units travel with values.** Because `value` is one column holding percent, N$ billion,
USD and person-counts, `unit` is mandatory on every row and the validator fails the build
if any row lacks one.

## Repository layout

```
├── config/
│   ├── indicators.json         World Bank codes + unit/category/label metadata
│   └── regions.json            10 grid points + the baseline period
├── src/
│   ├── common.py               paths, logging, HTTP-with-retries
│   ├── extract/                world_bank.py · climate.py
│   ├── transform/              climate_risk.py
│   ├── load/                   build_warehouse.py
│   ├── validate/               validate_data.py
│   └── docs_gen.py             regenerates docs/data_dictionary.md
├── data/
│   ├── automated/              API output, overwritten each run
│   ├── curated/                hand-maintained national statistics
│   ├── dimension/              energy mix, hydrogen pipeline, milestones
│   └── warehouse/              the star schema Power BI loads
├── powerbi/
│   ├── NamibiaDashboard.pbix
│   ├── measures.dax            the core measure set
│   └── themes/                 importable light + dark theme JSON
├── docs/
├── pipeline.py
└── .github/workflows/          update-data.yml (monthly) · ci.yml (per PR)
```
