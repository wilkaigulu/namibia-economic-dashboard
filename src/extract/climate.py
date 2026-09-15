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