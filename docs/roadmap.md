# Roadmap

## v1 — shipped
- World Bank economic, fiscal and trade indicators
- NASA POWER climate extract (single point)
- Flat `fact_indicator` table and a Power BI executive KPI strip

## v2 — current
- Star schema: `fact_indicator`, `fact_climate_monthly`, `dim_indicator`, `dim_date`, `dim_region`
- Units, frequency and forecast flags on every fact row
- SPI-based drought methodology, one-sided composite risk index, ordinal risk bands
- Ten regional climate grid points, fixed WMO baseline
- Fail-closed pipeline, 11-check validation gate, monthly CI refresh
- Validated light and dark Power BI themes; shared measure set

## v3 — next
- **Regional climate risk on a map** — the regional panel exists; the Namibia shapefile
  and a choropleth do not yet
- **Climate-to-macro linkage** — regress GDP growth and agricultural value added on
  lagged SPI-12; this is the analytical payload the dashboard is really for
- **Climate finance tracking** — commitments vs disbursements by facility, against the
  adaptation finance gap
- **Sovereign climate risk** — debt sustainability under drought-shock scenarios
- **Hydrogen project state machine** — track each project through FEED → FID → COD
  rather than as a static pipeline table
- **Station-network coverage layer** — overlay the sparse ground-station network on the
  reanalysis grid to show where the disclosure gap actually is

## Deliberately not doing
- Daily climate in the fact table (grain mismatch, model bloat)
- Dual-axis charts (two y-scales are unreadable; use two charts or index to a base)
- A live DirectQuery connection (the data changes monthly; import is correct here)
