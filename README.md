# Namibia Economic, Energy, Climate Risk & Green Hydrogen Observatory

A reproducible analytics platform monitoring Namibia's economic performance, public
finances, trade, energy transition, green hydrogen sector and climate risk — with a
Power BI front end over a Python-built star schema, refreshed monthly by GitHub Actions.

**Author:** Wilka Igulu — Climate Risk Research · Economic Analytics · Climate Finance

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python pipeline.py              # full refresh (hits World Bank + NASA POWER)
python pipeline.py --offline     # rebuild the warehouse from committed CSVs only
python pipeline.py --only load validate
python src/docs_gen.py           # regenerate docs/data_dictionary.md
```

Then open `powerbi/NamibiaDashboard.pbix` and refresh.

## Architecture

```
World Bank API ─┐
                ├─► data/automated/ ─┐
NASA POWER API ─┘                   │
                                    ├─► src/transform ─► src/load ─► data/warehouse/
NSA · BoN · MoF · NamPower ────────►│                                 fact_indicator
(hand-curated) data/curated/        │                                 fact_climate_monthly
                                    │                                 dim_indicator
Hydrogen & energy data/dimension/ ──┘                                 dim_date · dim_region
                                                                            │
                                               src/validate (quality gate) ─┤
                                                                            ▼
                                                                   Power BI model
```

The pipeline is fail-closed: any step that errors aborts the run, so the warehouse
keeps its last good build rather than publishing a partial refresh.

## Warehouse

| Table | Grain | Purpose |
|---|---|---|
| `fact_indicator` | indicator × date | every economic, fiscal, trade, labour and national climate series |
| `fact_climate_monthly` | region × month | SPI, temperature anomaly, composite risk per region |
| `dim_indicator` | indicator | label, unit, frequency, direction, benchmark |
| `dim_date` | month | calendar, Namibian fiscal year (Apr–Mar), rainfall season (Oct–Sep) |
| `dim_region` | region | the ten NASA POWER grid points and their zones |

Every fact row carries `unit`, `frequency` and `is_forecast`. `is_forecast` matters:
`data/curated/debt_to_gdp.csv` runs to 2029 and the last three years are IMF
projections, not outturns.

See [`docs/data_dictionary.md`](docs/data_dictionary.md) (generated) for all 27 series.

## Climate risk methodology

Drought is measured with **SPI** (Standardised Precipitation Index, McKee et al. 1993):
monthly rainfall accumulations over 1/3/6/12-month windows, gamma-fitted per calendar
month against a fixed baseline, with a point mass at zero. Heat is a standardised
temperature index against the same baseline. The composite is **one-sided** — only
rainfall deficit and heat excess count as risk — and reported in z-units plus an
ordinal band (Normal / Watch / Severe / Extreme).

Baseline: WMO 1991–2020 where the record allows; the transform falls back to the full
record and logs a warning when it does not.

## Dashboard pages

| Page | Question it answers |
|---|---|
| Executive Overview | Is Namibia's macro position improving, and is the climate adding stress right now? |
| Economy & Finance | Can the fiscus carry the debt, and what is inflation doing to households? |
| Trade & Competitiveness | What do we sell, what do we buy, and is the gap widening? |
| Climate & Energy | Where is drought biting, and how fast is the generation mix actually changing? |
| Green Hydrogen Observatory | What is committed, what is under construction, and what decides next? |

Design system — palette, layout grids, visual choices per page, DAX — lives in
`powerbi/themes/` (importable theme JSON), `powerbi/measures.dax`, and
`docs/dashboard_design.md`.

## Data sources

**Automated:** World Bank Indicators API · NASA POWER (daily T2M, T2M_MAX, PRECTOTCORR)

**Curated (updated by hand, quarterly):** Namibia Statistics Agency · Bank of Namibia ·
Ministry of Finance · NamPower · Namibia Green Hydrogen Programme

## Known data caveats

- `electricity_generation.csv` mixes two different measures: `Percentage` is share of
  *energy supplied*, `Installed_Capacity_MW` is nameplate capacity. Solar is 24% of
  capacity but 4% of supply. Never plot them on one axis.
- `energy_security.csv` reports renewable share at 21%, while the generation mix implies
  ~40% (hydro 35 + solar 4 + wind 1). These are different definitions — reconcile before
  publishing either as "the" renewable share.
- Trade figures for 2020–2023 are round numbers and look like estimates; 2024–2025 are
  precise. Treat the early years as indicative.
- `UNEMPLOYMENT_STRICT/BROAD/YOUTH` have three observations each (2016, 2018, 2023).
  That is a survey series, not a trend line — plot as columns, not a line.

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md).

## Licence

See [`LICENSE`](LICENSE).
