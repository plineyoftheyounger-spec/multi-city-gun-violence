"""
auto_update_all.py
───────────────────
Monthly incremental update for all 6 cities, ported from
orlando_gun_violence/06_auto_update.py:main() and generalized to loop over
cities.CITIES. For each city: fetch new incidents since the last processed
date, geocode them, merge into the processed CSV, and rebuild that city's map.

Run manually:
    python auto_update_all.py

Scheduled via GitHub Actions — see .github/workflows/monthly-update.yml.
Logs written to: output/update_log.txt
"""

import logging
import sys
import time
from datetime import date, timedelta

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cities
import gva_common
from fetch_gva import download_gva_csv
from geocode_census import geocode_batch
from build_maps import build_map_for_city
from export_explorer_data import export as export_explorer_data
from looker_export import export as export_looker_csv

# Same courtesy pacing as backfill.py — GVA's anti-bot filter blocks an IP
# after a handful of rapid automated queries.
REQUEST_DELAY_SECONDS = 45

LOG_FILE = cities.ROOT / "output" / "update_log.txt"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def update_city(slug: str):
    cfg = cities.CITIES[slug]
    path = cities.processed_csv(slug)
    if not path.exists():
        log.warning(f"{slug}: no processed CSV found — run backfill.py first. Skipping.")
        return

    existing = pd.read_csv(path, parse_dates=["date"])
    last_date = existing["date"].max().date()
    today = date.today()
    start = last_date + timedelta(days=1)

    if start > today:
        log.info(f"{cfg['display_name']}: already current through {last_date}.")
        build_map_for_city(slug)
        return

    log.info(f"{cfg['display_name']}: current through {last_date}; fetching {start} to {today}")

    raw_dir = cities.raw_dir(slug)
    raw_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = cities.OUTPUT_DIR / slug / "debug"
    filename = f"gva_{slug}_{start.strftime('%Y%m%d')}_{today.strftime('%Y%m%d')}.csv"
    csv_path = raw_dir / filename

    time.sleep(REQUEST_DELAY_SECONDS)
    download_gva_csv(cfg["gva_state"], cfg["gva_city"], start, today, csv_path, debug_dir)

    raw_df = pd.read_csv(csv_path, dtype=str)
    raw_df.columns = raw_df.columns.str.strip()
    raw_df = gva_common.normalise_columns(raw_df)
    fresh = gva_common.clean(raw_df)
    fresh = geocode_batch(fresh, cfg["gva_city"], cfg["gva_state"])

    updated, new_count = gva_common.merge(existing, fresh)
    if new_count <= 0:
        log.info(f"{cfg['display_name']}: no new incidents after dedup.")
        return

    updated.to_csv(path, index=False)
    new_last = updated["date"].max().date()
    log.info(f"{cfg['display_name']}: added {new_count:,} incidents | "
             f"total {len(updated):,} | now through {new_last}")

    build_map_for_city(slug)


def main():
    log.info("=" * 50)
    log.info("Multi-city GVA auto-update starting")
    for slug in cities.CITIES:
        try:
            update_city(slug)
        except Exception:
            log.exception(f"Update failed for {slug}")

    try:
        export_explorer_data()
    except Exception:
        log.exception("Explorer data export failed")

    try:
        export_looker_csv()
    except Exception:
        log.exception("Looker CSV export failed")

    log.info("Multi-city GVA auto-update complete")


if __name__ == "__main__":
    main()
