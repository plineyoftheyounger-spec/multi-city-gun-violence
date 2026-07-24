"""
geocode_census.py
──────────────────
Bulk geocoding via the US Census Bureau's free batch geocoder. Needed because
GVA's current CSV export only provides street addresses, not lat/lon (older
exports Orlando was originally seeded with did include coordinates; GVA has
since dropped them from the query tool's export — Orlando's newest rows are
already silently missing coordinates as a result).

API: https://geocoding.geo.census.gov/geocoder/locations/addressbatch
Free, no API key, accepts up to 10,000 addresses per request, public-domain
TIGER/Line-based matching. Built for exactly this kind of bulk/automated use.
"""

import io
import logging
import re

import pandas as pd
import requests

log = logging.getLogger(__name__)

BATCH_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
BENCHMARK = "Public_AR_Current"
MAX_BATCH = 10_000

_BLOCK_RE = re.compile(r"^(\d+)\s+block of\s+(.+)$", re.IGNORECASE)


def _normalize_address(addr) -> str:
    """GVA often redacts to '9700 block of Main St' — use the block number as
    an approximate house number so the geocoder still has something to match."""
    addr = "" if pd.isna(addr) else str(addr).strip()
    m = _BLOCK_RE.match(addr)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return addr


def _csv_field(v: str) -> str:
    return '"' + str(v).replace('"', '""') + '"'


def _build_input_csv(df: pd.DataFrame, city: str, state: str) -> bytes:
    """Census batch format: Unique ID, Street address, City, State, ZIP (no header)."""
    lines = []
    for idx, row in df.iterrows():
        addr = _normalize_address(row.get("address", ""))
        lines.append(",".join([
            str(idx), _csv_field(addr), _csv_field(city), _csv_field(state), ""
        ]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def geocode_batch(df: pd.DataFrame, city: str, state: str) -> pd.DataFrame:
    """Fill lat/lon for rows currently missing them. Returns a new DataFrame;
    rows the geocoder can't match are left with null lat/lon (dropped later,
    same as any other unmapped incident)."""
    missing = df["lat"].isna() | df["lon"].isna()
    to_geocode = df[missing]
    if to_geocode.empty:
        return df

    df = df.copy()
    total_matched = 0
    ids = to_geocode.index.tolist()

    for start in range(0, len(ids), MAX_BATCH):
        chunk_ids = ids[start:start + MAX_BATCH]
        chunk = to_geocode.loc[chunk_ids]
        input_csv = _build_input_csv(chunk, city, state)

        log.info(f"  Geocoding {len(chunk):,} addresses via Census Bureau batch API...")
        resp = requests.post(
            BATCH_URL,
            files={"addressFile": ("addresses.csv", input_csv, "text/csv")},
            data={"benchmark": BENCHMARK},
            timeout=180,
        )
        resp.raise_for_status()

        result = pd.read_csv(
            io.StringIO(resp.text), header=None,
            names=["id", "input_address", "match", "match_type",
                   "matched_address", "coordinates", "tiger_line_id", "side"],
            dtype=str,
        )

        matched = result[result["match"] == "Match"]
        for _, r in matched.iterrows():
            try:
                lon_str, lat_str = r["coordinates"].split(",")
                df.at[int(r["id"]), "lon"] = float(lon_str)
                df.at[int(r["id"]), "lat"] = float(lat_str)
            except Exception:
                continue
        total_matched += len(matched)

    rate = total_matched / len(to_geocode) if len(to_geocode) else 0
    log.info(f"  Geocoded {total_matched:,} of {len(to_geocode):,} addresses ({rate:.0%} match rate)")
    return df
