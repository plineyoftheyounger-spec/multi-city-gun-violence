"""
backfill.py
───────────
One-time historical pull per city, chunked by calendar year (GVA's export tool
caps rows per query, so a single multi-year request isn't reliable — chunking
by year mirrors how Orlando's dataset was originally built by hand, just
automated here).

Usage:
    python backfill.py                  # all 6 cities
    python backfill.py austin miami     # just these cities

Downloads land in data/<slug>/raw/, one CSV per year. Already-downloaded raw
CSVs are reused on re-run (so a failed run partway through can be resumed
without re-fetching everything). The cleaned, merged result is written to
data/<slug>/processed/<slug>_incidents.csv.
"""

import logging
import sys
import time
from datetime import date

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cities
import gva_common
from fetch_gva import download_gva_csv
from geocode_census import geocode_batch

# GVA's anti-bot filter flags rapid sequential automated queries (observed
# after ~11 requests in 5 minutes) and blocks the IP with "please try again
# later." Space requests out and back off hard on failure rather than
# hammering it — this is a courtesy pacing limit, not a workaround.
REQUEST_DELAY_SECONDS = 45

LOG_FILE = cities.ROOT / "output" / "backfill_log.txt"
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


def year_chunks(start_year: int, today: date):
    """[(start, end), ...] one per calendar year, last chunk clipped to today."""
    chunks = []
    for y in range(start_year, today.year + 1):
        start = date(y, 1, 1)
        end = date(y, 12, 31) if y < today.year else today
        chunks.append((start, end))
    return chunks


def backfill_city(slug: str):
    cfg = cities.CITIES[slug]
    today = date.today()
    start_year = cfg["era"]["pre_start"].year if cfg["mode"] == "era" else cfg["start_year"]

    raw_dir = cities.raw_dir(slug)
    raw_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = cities.OUTPUT_DIR / slug / "debug"

    log.info(f"── {cfg['display_name']} ({slug}): backfilling {start_year}-{today.year} ──")

    frames = []
    for start, end in year_chunks(start_year, today):
        filename = f"gva_{slug}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
        out_path = raw_dir / filename

        if out_path.exists():
            log.info(f"  {filename} already downloaded, reusing")
        else:
            log.info(f"  Waiting {REQUEST_DELAY_SECONDS}s before next GVA request...")
            time.sleep(REQUEST_DELAY_SECONDS)
            download_gva_csv(cfg["gva_state"], cfg["gva_city"], start, end, out_path, debug_dir)

        raw_df = pd.read_csv(out_path, dtype=str)
        raw_df.columns = raw_df.columns.str.strip()
        raw_df = gva_common.normalise_columns(raw_df)
        year_clean = gva_common.clean(raw_df)
        year_clean = geocode_batch(year_clean, cfg["gva_city"], cfg["gva_state"])
        no_coords = year_clean["lat"].isna().sum()
        log.info(f"  {start.year}: {len(year_clean):,} incidents "
                 f"({no_coords} unmapped after geocoding)")
        frames.append(year_clean)

    combined = pd.concat(frames, ignore_index=True)
    if "incident_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["incident_id"])
    else:
        combined = combined.drop_duplicates(subset=["date", "address"])
    combined = combined.sort_values("date").reset_index(drop=True)

    out = cities.processed_csv(slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out, index=False)
    log.info(f"  Saved {len(combined):,} total incidents -> {out}")


def main():
    slugs = sys.argv[1:] or list(cities.CITIES.keys())
    unknown = [s for s in slugs if s not in cities.CITIES]
    if unknown:
        raise SystemExit(f"Unknown city slug(s): {unknown}. Valid: {list(cities.CITIES)}")

    for slug in slugs:
        try:
            backfill_city(slug)
        except Exception:
            log.exception(f"Backfill failed for {slug}")


if __name__ == "__main__":
    main()
