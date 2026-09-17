import pandas as pd

rain = pd.read_csv(
    "data/automated/climate/rainfall.csv"
)

temp = pd.read_csv(
    "data/automated/climate/temperature.csv"
)

rain["rain_anomaly"] = (
    rain["value"]
    - rain["value"].mean()
)

temp["temp_anomaly"] = (
    temp["value"]
    - temp["value"].mean()
)

rain["rain_z"] = (
    rain["rain_anomaly"]
    / rain["rain_anomaly"].std()
)

temp["temp_z"] = (
    temp["temp_anomaly"]
    / temp["temp_anomaly"].std()
)

climate = rain.merge(
    temp,
    on="date",
    suffixes=("_rain", "_temp")
)

climate["climate_risk_index"] = (
    0.5 * abs(climate["rain_z"])
    + 0.5 * abs(climate["temp_z"])
)

climate.to_csv(
    "data/automated/climate/climate_risk_composite.csv",
    index=False
)