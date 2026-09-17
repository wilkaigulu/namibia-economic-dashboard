# Namibia Economic, Energy, Climate Risk & Green Hydrogen Observatory

A data-driven analytics platform for monitoring Namibia's economic performance, public finances, trade, energy transition, green hydrogen sector and climate risks. 

## Project Objectives

The project provides a centralized framework for:

- Economic monitoring
- Fiscal sustainability analysis
- Trade performance tracking
- Energy transition assesment 
- Green hydrogen ecosystem monitoring
- Climate risks analytics

## Technology Stack

- Python
- Pandas
- Git 
- GitHub Actions
- Power BI

## Data Sources

### Automated Sources

- World Bank API
- NASA POWER API

### Curated Sources

- Namibia Statistics Agency (NSA)
- Bank of Namibia (BoN)
- Ministry of Finance
- NamPower
- Green Hydrogen Reports

## Repository Structure 

```text 
namibia-economic-dashboard/

├── data/
│   ├── automated/
│   │   ├── world_bank/
│   │   └── climate/
│   │
│   ├── curated/
│   │
│   └── warehouse/
│       └── fact_indicator.parquet
│
├── src/
│   ├── extract/
│   ├── transform/
│   ├── validate/
│   └── load/
│
├── docs/
│
├── powerbi/
│
└── .github/workflows/
```

## Dashboard Modules

### Executive Overview

- GDP Growth
- Inflation
- Debt-to-GDP
- Trade Balance
- Climate Risk Index

### Economy

- GDP Growth
- GDP per Capita
- Population
- Inflation

### Finance

- Debt-to-GDP
- Fiscal Deficit
- Total Debt

### Trade

- Exports
- Imports
- Trade Balance

### Energy

- Generation Mix
- Renewable Share
- Energy Security

### Green Hydrogen

- FDI Tracking
- Project Pipeline
- Industry Announcements
- Key Milestones

### Climate Risk

- Rainfall
- Temperature
- Drought Score
- Temperature Anomaly
- Rainfall Anomaly
- Climate Risk Composite

## Outputs

- fact_indicator.parquet
- Power BI Dashboard
- Climate Risk Analytics
- Quarterly Economic Monitoring Reports

## Future Enhancements

- Regional climate risk analysis
- Climate finance tracking
- Infrastructure risk indicators
- Sovereign climate risk metrics
- ESG and sustainable finance indicators

## Author

Wilka Igulu

Climate Risk Research | Economic Analytics | Climate Finance