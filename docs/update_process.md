# Update process

## Automated — monthly, no action needed

`.github/workflows/update-data.yml` runs at 04:00 UTC (06:00 Windhoek) on the 1st of
each month, and on demand via **Actions → Update dashboard data → Run workflow**.

It extracts, transforms, loads, validates, writes a build summary to the run page,
uploads `data/warehouse/` as an artefact (even on failure), and commits the refreshed
CSV and Parquet files only if every step passed.

If the run goes red, open it and read the validation report — the failing check names
the problem (a range breach, a missing unit, an unflagged projection, a >10% row-count
drop). Nothing was committed, so the dashboard is still showing the last good data.

## Quarterly — the curated files

The APIs cover the automated half. These four still need a human:

1. **NSA** — trade: update `data/curated/trade_balance.csv` from the monthly trade
   statistics bulletin. Labour: update `data/curated/unemployment.csv` only when a new
   Labour Force Survey lands (last: 2023).
2. **Bank of Namibia** — update `data/curated/inflation_history.csv` and the repo-rate
   row in `data/dimension/kpi_summary.csv` from the latest MPC statement.
3. **Ministry of Finance / IMF Article IV** — update `data/curated/debt_to_gdp.csv`.
   **When you add a year, check `FORECAST_FROM` in `src/load/build_warehouse.py`** — it
   is what separates outturns from projections, and the validator fails the build if a
   future-dated row is not flagged.
4. **NamPower / NGH2P** — update `data/dimension/generation_pipeline.csv`,
   `hydrogen_announcements.csv`, `green_fdi_funding.csv` and `milestones.csv`.

Then:

```bash
python pipeline.py --offline   # rebuild + validate without hitting the APIs
python src/docs_gen.py         # refresh the data dictionary
```

Commit, push, and refresh the Power BI model.

## Changing an indicator

- **Adding a World Bank series** — add an entry to `config/indicators.json` with its
  code, category, unit and label. Nothing else needs touching; the extractor and loader
  both read the config.
- **Adding a curated series** — add a row to `CURATED_SOURCES` in
  `src/load/build_warehouse.py`, and a plausible range to `RANGES` in
  `src/validate/validate_data.py`.
- **Adding a climate region** — add it to `config/regions.json` and re-run the climate
  extract. One entry is one API call.
