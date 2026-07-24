"""
gva_common.py
─────────────
City-agnostic GVA column handling and cleaning, shared by backfill.py and
auto_update_all.py. Ported from orlando_gun_violence/config.py + 01_prepare_data.py
+ 06_auto_update.py, generalized to drop Orlando-specific assumptions.
"""

import pandas as pd

# ── GVA CSV column names (older "download" export format) ─────────────────────
COL_ID      = "id"
COL_DATE    = "date"
COL_STATE   = "state"
COL_CITY    = "city"
COL_ADDRESS = "address"
COL_KILLED  = "number_killed"
COL_INJURED = "number_injured"
COL_LAT     = "latitude"
COL_LON     = "longitude"

COL_FLAGS = ["child_involved", "officer_involved", "mass_shooting",
             "accidental", "domestic_violence", "drive_by"]

# ── Newer "human-readable header" export format ────────────────────────────────
_NEW_COL_MAP = {
    "Incident ID":     COL_ID,
    "Incident Date":   COL_DATE,
    "State":           COL_STATE,
    "City Or County":  COL_CITY,
    "Address":         COL_ADDRESS,
    "Victims Killed":  COL_KILLED,
    "Victims Injured": COL_INJURED,
}


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename new-format GVA columns to the internal names clean() expects."""
    rename = {k: v for k, v in _NEW_COL_MAP.items() if k in df.columns}
    if rename:
        df = df.rename(columns=rename)
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    required = [COL_DATE, COL_KILLED, COL_INJURED]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing expected columns: {missing_cols}\n"
            f"Found columns: {list(df.columns)}"
        )

    rename_map = {
        COL_ID: "incident_id", COL_DATE: "date", COL_STATE: "state",
        COL_CITY: "city", COL_ADDRESS: "address",
        COL_KILLED: "killed", COL_INJURED: "injured",
    }
    rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    if COL_LAT in df.columns and COL_LON in df.columns:
        df = df.rename(columns={COL_LAT: "lat", COL_LON: "lon"})
    else:
        df["lat"] = None
        df["lon"] = None

    df["date"]    = pd.to_datetime(df["date"], errors="coerce")
    df["killed"]  = pd.to_numeric(df["killed"],  errors="coerce").fillna(0).astype(int)
    df["injured"] = pd.to_numeric(df["injured"], errors="coerce").fillna(0).astype(int)
    df["lat"]     = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"]     = pd.to_numeric(df["lon"], errors="coerce")

    for col in COL_FLAGS:
        if col in df.columns:
            df[col] = df[col].map(
                {"True": True, "False": False, True: True, False: False}
            ).fillna(False).astype(bool)

    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["total"] = df["killed"] + df["injured"]
    df["fatal"] = df["killed"] > 0
    if "mass_shooting" in df.columns:
        df["mass"] = df["mass_shooting"]
    else:
        df["mass"] = df["total"] >= 4

    before = len(df)
    if "incident_id" in df.columns:
        df = df.drop_duplicates(subset=["incident_id"])
    else:
        df = df.drop_duplicates(subset=["date", "address"])
    after = len(df)
    if before != after:
        print(f"  Removed {before - after:,} duplicate rows.")

    df = df.dropna(subset=["date"])

    print(f"  Cleaned: {len(df):,} incidents | "
          f"{df['killed'].sum():,} killed | {df['injured'].sum():,} injured")
    return df.sort_values("date").reset_index(drop=True)


def merge(existing: pd.DataFrame, fresh: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    combined = pd.concat([existing, fresh], ignore_index=True)
    if "incident_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["incident_id"])
    else:
        combined = combined.drop_duplicates(subset=["date", "address"])
    combined = combined.sort_values("date").reset_index(drop=True)
    return combined, len(combined) - len(existing)
