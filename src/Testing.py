import pandas as pd

df = pd.read_parquet("data/warehouse/fact_indicator.parquet"

)

print(df.shape)

print(df["indicator"].unique())