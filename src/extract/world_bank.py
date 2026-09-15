#src/extract/world_bank.py

import json
import requests
import pandas as pd

COUNTRY = "NAM"

with open("config/indicators.json", "r") as f:
    indicators = json.load(f)

for name, code in indicators.items():

    url = (
        f"https://api.worldbank.org/v2/country/"
        f"{COUNTRY}/indicator/{code}"
        "?format=json"
        "&date=2000:2025"
        "&per_page=100"
    )

    response = requests.get(url)

    if response.status_code != 200:
        continue

    data = response.json()

    if len(data) < 2:
        continue

    rows = []

    for item in data[1]:

        if item["value"] is None:
            continue

        rows.append({
            "date": item["date"],
            "value": item["value"]
        })

    df = pd.DataFrame(rows)

    df.to_csv(
        f"data/automated/world_bank/{name.lower()}.csv",
        index=False
    )

print("World Bank download complete")