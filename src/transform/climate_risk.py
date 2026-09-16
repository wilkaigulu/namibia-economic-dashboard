import pandas as pd

rain = pd.read_csv("data/automated/climate/rainfall.csv")

mean = rain["value"].mean()

std = rain["value"].std()

rain["drought_score"] = (
    rain["value"] - mean
) / std

rain.to_csv(
    "data/automated/climate/climate_risk_index.csv",
    index=False
)