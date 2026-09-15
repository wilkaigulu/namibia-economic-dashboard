import pandas as pd

df = pd.read_csv(
    "data/warehouse/fact_indicator.csv"
)

assert len(df) > 0

assert "date" in df.columns

assert "value" in df.columns

print("Validation passed")


