# scr/load/build_warehouse.py

import pandas as pd
from pathlib import Path

records = []

# --------------------------------------------------
# helper
# --------------------------------------------------

def add_indicator(
    df,
    date_col,
    value_col,
    indicator,
    source,
    category
):

    temp = pd.DataFrame({

        "date":
            df[date_col],

        "indicator":
            indicator,

        "value":
            df[value_col],

        "source":
            source,

        "category":
            category
    })

    records.append(temp)


def standardize_date(series):

    s = series.astype(str).str.strip()

    # Annual indicators
    annual_mask = s.str.match(r"^\d{4}$")

    result = pd.Series(index=s.index, dtype="datetime64[ns]")

    result.loc[annual_mask] = pd.to_datetime(
        s.loc[annual_mask] + "-01-01"
    )

    # Daily climate indicators
    result.loc[~annual_mask] = pd.to_datetime(
        s.loc[~annual_mask],
        format="%Y%m%d",
        errors="coerce"
    )

    return result

# --------------------------------------------------
# WORLD BANK
# --------------------------------------------------

wb = Path("data/automated/world_bank")

world_bank_files = {

    "gdp_growth.csv":
        ("GDP_GROWTH","Economy"),

    "gdp_per_capita.csv":
        ("GDP_PER_CAPITA","Economy"),

    "population.csv":
        ("POPULATION","Economy"),

    "fdi.csv":
        ("FDI","Finance"),

    "debt_gdp.csv":
        ("DEBT_GDP_WB","Finance"),

    "trade_gdp.csv":
        ("TRADE_GDP","Trade"),

    "unemployment.csv":
        ("UNEMPLOYMENT_WB","Labour")
}

for file, meta in world_bank_files.items():

    path = wb / file

    if not path.exists():
        continue

    df = pd.read_csv(path)

    if "date" not in df.columns:
        continue

    if "value" not in df.columns:
        continue

    add_indicator(
        df,
        "date",
        "value",
        meta[0],
        "World Bank",
        meta[1]
    )

# --------------------------------------------------
# DEBT
# --------------------------------------------------

debt = pd.read_csv(
    "data/curated/debt_to_gdp.csv"
)

add_indicator(
    debt,
    "Year",
    "Debt_to_GDP_Pct",
    "DEBT_GDP",
    "Ministry of Finance",
    "Finance"
)

add_indicator(
    debt,
    "Year",
    "Total_Debt_NS_Billion",
    "TOTAL_DEBT",
    "Ministry of Finance",
    "Finance"
)

add_indicator(
    debt,
    "Year",
    "Fiscal_Deficit_Pct",
    "FISCAL_DEFICIT",
    "Ministry of Finance",
    "Finance"
)

# --------------------------------------------------
# INFLATION
# --------------------------------------------------

inflation = pd.read_csv(
    "data/curated/inflation_history.csv"
)

add_indicator(
    inflation,
    "Year",
    "Inflation_Rate_Pct",
    "INFLATION",
    "Bank of Namibia",
    "Economy"
)

# --------------------------------------------------
# UNEMPLOYMENT
# --------------------------------------------------

unemp = pd.read_csv(
    "data/curated/unemployment.csv"
)

add_indicator(
    unemp,
    "Survey_Year",
    "Strict_Unemployment_Pct",
    "UNEMPLOYMENT_STRICT",
    "NSA",
    "Labour"
)

add_indicator(
    unemp,
    "Survey_Year",
    "Broad_Unemployment_Pct",
    "UNEMPLOYMENT_BROAD",
    "NSA",
    "Labour"
)

# --------------------------------------------------
# TRADE
# --------------------------------------------------

trade = pd.read_csv(
    "data/curated/trade_balance.csv"
)

add_indicator(
    trade,
    "Year",
    "Exports_NS_Million",
    "EXPORTS",
    "NSA",
    "Trade"
)

add_indicator(
    trade,
    "Year",
    "Imports_NS_Million",
    "IMPORTS",
    "NSA",
    "Trade"
)

add_indicator(
    trade,
    "Year",
    "Balance_NS_Million",
    "TRADE_BALANCE",
    "NSA",
    "Trade"
)

# --------------------------------------------------
# CLIMATE
# --------------------------------------------------

rain = pd.read_csv(
    "data/automated/climate/rainfall.csv"
)

add_indicator(
    rain,
    "date",
    "value",
    "RAINFALL",
    "NASA",
    "Climate"
)

temp = pd.read_csv(
    "data/automated/climate/temperature.csv"
)

add_indicator(
    temp,
    "date",
    "value",
    "TEMPERATURE",
    "NASA",
    "Climate"
)

risk = pd.read_csv(
    "data/automated/climate/climate_risk_index.csv"
)

add_indicator(
    risk,
    "date",
    "drought_score",
    "DROUGHT_SCORE",
    "Derived",
    "Climate"
)

climate_composite = pd.read_csv(
    "data/automated/climate/climate_risk_composite.csv"
)

add_indicator(
    climate_composite,
    "date",
    "climate_risk_index",
    "CLIMATE_RISK_INDEX",
    "Derived",
    "Climate"
)

# --------------------------------------------------
# BUILD WAREHOUSE
# --------------------------------------------------

warehouse = pd.concat(
    records,
    ignore_index=True
)

warehouse = warehouse.dropna(
    subset=["value"]
)

warehouse["date"] = standardize_date(warehouse["date"])

warehouse["year"] = warehouse["date"].dt.year
warehouse["month"] = warehouse["date"].dt.month
warehouse["quarter"] = warehouse["date"].dt.quarter

warehouse = warehouse.sort_values(
    ["date", "indicator"]
)

warehouse.to_csv(
    "data/warehouse/fact_indicator.csv",
    index=False
)

warehouse.to_parquet(
    "data/warehouse/fact_indicator.parquet",
    index=False
)


print(
    f"Warehouse rows: {len(warehouse):,}"
)

print(
    warehouse["indicator"].unique()
)