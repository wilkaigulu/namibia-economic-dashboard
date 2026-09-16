import requests
import pandas as pd

LAT = -22.56
LON = 17.08

url = (
    "https://power.larc.nasa.gov/api/temporal/daily/point"
    "?parameters=T2M,PRECTOTCORR"
    "&community=AG"
    f"&longitude={LON}"
    f"&latitude={LAT}"
    "&start=2000"
    "&end=2025"
    "&format=JSON"
)

response = requests.get(url)

data = response.json()

temps = data["properties"]["parameter"]["T2M"]
rain = data["properties"]["parameter"]["PRECTOTCORR"]

temp_df = pd.DataFrame(
    list(temps.items()),
    columns=["date", "value"]
)

temp_df.to_csv(
    "data/curated/temperature.csv",
    index=False
)

rain_df = pd.DataFrame(
    list(rain.items()), 
    columns=["date", "value"]
)

rain_df.to_csv(
    "data/curated/rainfall.csv",
    index=False
)

print("Climate data saved")


