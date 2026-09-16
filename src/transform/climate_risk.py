import pandas as pd

rain = pd.read_csv("data/curated/rainfall.csv")

mean = rain["value"].mean()

std = rain["value"].std()

rain["drought_score"] = (
    rain["value"] - mean
) / std

rain.to_csv(
    "data/curated/climate_risk_index.csv",
    index=False
)
