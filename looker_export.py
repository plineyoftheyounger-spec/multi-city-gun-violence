"""
looker_export.py
─────────────────
Builds one long-format CSV across all cities, shaped for a Google Sheet that
Looker Studio reads from — one row per incident, clean Title Case headers
Looker will pick up as field names automatically.

v1 has no Google API credentials wired up: run this, then in Google Sheets
use File > Import > Upload (or Insert > Sheet from CSV) to load
output/looker_export.csv, and point a Looker Studio data source at that
sheet. Re-run and re-import whenever the underlying data changes (e.g. after
auto_update_all.py) to refresh it.

Run directly:
    python looker_export.py
"""

import pandas as pd

import cities

OUT_PATH = cities.OUTPUT_DIR / "looker_export.csv"

COLUMNS = {
    "incident_id": "Incident ID",
    "date": "Date",
    "year": "Year",
    "month": "Month",
    "display_name": "City",
    "state": "State",
    "address": "Address",
    "killed": "Killed",
    "injured": "Injured",
    "total": "Total Victims",
    "fatal": "Fatal Incident",
    "mass": "Mass Shooting",
    "lat": "Latitude",
    "lon": "Longitude",
}


def export():
    frames = []
    for slug, cfg in cities.CITIES.items():
        path = cities.processed_csv(slug)
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["date"])
        df["display_name"] = cfg["display_name"]
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined[list(COLUMNS.keys())].rename(columns=COLUMNS)
    combined["Date"] = combined["Date"].dt.strftime("%Y-%m-%d")
    combined = combined.sort_values(["City", "Date"])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(combined):,} rows across {combined['City'].nunique()} cities -> {OUT_PATH}")


if __name__ == "__main__":
    export()
