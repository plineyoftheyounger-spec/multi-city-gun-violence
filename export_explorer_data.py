"""
export_explorer_data.py
────────────────────────
Combines every city's processed CSV into one compact JSON file that the
interactive pre/post explorer (explorer.html) fetches client-side. Keeping
this separate from build_maps.py's Folium output means the explorer can let
a viewer pick their own date windows and area at view time, instead of
baking a fixed split in at build time.

Run directly, or import export() and call it from auto_update_all.py:
    python export_explorer_data.py
"""

import json

import pandas as pd

import cities

OUT_PATH = cities.OUTPUT_DIR / "explorer_data.json"


def export():
    cities_out = []
    incidents = []

    for slug, cfg in cities.CITIES.items():
        path = cities.processed_csv(slug)
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["date"])
        df = df.dropna(subset=["lat", "lon"])

        cities_out.append({
            "slug": slug,
            "name": cfg["display_name"],
            "lat": cfg["lat"],
            "lon": cfg["lon"],
            "zoom": cfg["zoom"],
        })

        for _, row in df.iterrows():
            incidents.append({
                "id": row.get("incident_id"),
                "city": slug,
                "date": row["date"].strftime("%Y-%m-%d"),
                "lat": round(float(row["lat"]), 6),
                "lon": round(float(row["lon"]), 6),
                "k": int(row["killed"]),
                "i": int(row["injured"]),
                "m": bool(row.get("mass", False)),
                "a": row.get("address", "") if pd.notna(row.get("address", "")) else "",
            })

    payload = {"cities": cities_out, "incidents": incidents}

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))

    print(f"Wrote {len(incidents):,} incidents across {len(cities_out)} cities -> {OUT_PATH}")


if __name__ == "__main__":
    export()
