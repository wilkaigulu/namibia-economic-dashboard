import pandas as pd
from pathlib import Path

all_frames = []

folders = [
    "data/automated/world_bank",
    "data/manual/bank_of_namibia",
    "data/manual/nsa",
    "data/manual/climate",
    "data/manual/hydrogen"
]

for folder in folders:

    for file in Path(folder).glob("*.csv"):

        try:

            df = pd.read_csv(file)

            df["indicator"] = file.stem

            all_frames.append(df)

        except:
            pass

combined = pd.contact(
    all_frames,
    ignore_index=True
)

combined.to.csv(
    "data/warehouse/fact_indicator.csv",
    index=False
)

print("Standardization complete")