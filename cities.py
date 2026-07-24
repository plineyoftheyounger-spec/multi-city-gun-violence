"""
cities.py
─────────
Per-city configuration for the multi-city Gun Violence Archive project.

Two map "modes":
  "era"   — fixed pre/post intervention split (Milwaukee).
  "years" — one togglable layer per calendar year, from start_year to present
            (Austin, Miami, Jackson MS, Cleveland, Tucson).
"""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

CITIES = {
    "milwaukee": {
        "display_name": "Milwaukee",
        "gva_state": "Wisconsin",
        "gva_city": "Milwaukee",
        "lat": 43.0389,
        "lon": -87.9065,
        "zoom": 11,
        "mode": "era",
        "era": {
            "pre_label": "Pre-Intervention (Jan 2019 – Aug 2024)",
            "pre_start": date(2019, 1, 1),
            "pre_end": date(2024, 8, 31),
            "post_label": "Post-Intervention (Sep 2024 – Present)",
            "post_start": date(2024, 9, 1),
        },
    },
    "austin": {
        "display_name": "Austin",
        "gva_state": "Texas",
        "gva_city": "Austin",
        "lat": 30.2672,
        "lon": -97.7431,
        "zoom": 11,
        "mode": "years",
        "start_year": 2018,
    },
    "miami": {
        "display_name": "Miami",
        "gva_state": "Florida",
        "gva_city": "Miami",
        "lat": 25.7617,
        "lon": -80.1918,
        "zoom": 12,
        "mode": "years",
        "start_year": 2018,
    },
    "jackson_ms": {
        "display_name": "Jackson, MS",
        "gva_state": "Mississippi",
        "gva_city": "Jackson",
        "lat": 32.2988,
        "lon": -90.1848,
        "zoom": 11,
        "mode": "years",
        "start_year": 2018,
    },
    "cleveland": {
        "display_name": "Cleveland",
        "gva_state": "Ohio",
        "gva_city": "Cleveland",
        "lat": 41.4993,
        "lon": -81.6944,
        "zoom": 11,
        "mode": "years",
        "start_year": 2018,
    },
    "tucson": {
        "display_name": "Tucson",
        "gva_state": "Arizona",
        "gva_city": "Tucson",
        "lat": 32.2226,
        "lon": -110.9747,
        "zoom": 11,
        "mode": "years",
        "start_year": 2018,
    },
}


def raw_dir(slug: str) -> Path:
    return DATA_DIR / slug / "raw"


def processed_csv(slug: str) -> Path:
    return DATA_DIR / slug / "processed" / f"{slug}_incidents.csv"


def maps_dir(slug: str) -> Path:
    return OUTPUT_DIR / slug / "maps"
