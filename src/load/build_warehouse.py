# scr/load/build_warehouse.py

import pandas as pd

df = pd.read_csv(
    "data/warehouse/fact_indicator.csv"
)

df.to_parquet(
    "data/warehouse/fact_indicator.parquet",
    index=False
)

print("Warehouse built")

