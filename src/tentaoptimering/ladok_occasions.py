"""Reconciliation of the Ladok activity-occasion list (*Ladok ALLA aktivitetstillfällen*) with the prepared underlay.

The list is a different grain from the Ladok extract the model's demand rests on (`ladok_activities.csv`, one row per course
and occasion with total, registered and cancelled counts): it holds every published and draft activity occasion with its
`Prefix`, place, number of places and number registered. It reaches further in time than the extract. This module only
*measures* how it relates to the bookings and the existing extract (coverage per month, matches on prefix and date, whether
the registered counts agree). It never writes demand: whether `Antal anmälda` may be used as a demand measure, and for which
months, is a decision for the business that is recorded in `docs/BLOCKERANDE_DATAGAP.md`.

Run: `python -m tentaoptimering.ladok_occasions [source_dir] [processed_dir]` prints the reconciliation as JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

HEADER_ROW = 5  # the export starts with four metadata rows and an empty row
COLUMNS = ["status", "name", "datum", "ort", "lokal", "platser", "anmalda", "kurskod", "kurs", "kurstillfalle", "modul", "anmalningsperiod",
           "anonymt", "prefix", "ansvarig", "typ", "senast_andrad", "info", "installd"]
KEPT_STATUS = ("Publicerat", "Utkast")


def load_occasions(path: Path) -> pd.DataFrame:
    """The occasion rows with stable column names. Repeated header rows and other text in the status column are dropped and counted."""
    raw = pd.read_excel(path, header=HEADER_ROW)
    if raw.shape[1] < 16:
        raise ValueError(f"Oväntat antal kolumner i {Path(path).name}: {raw.shape[1]}. Källschemat behöver granskas.")
    raw = raw.iloc[:, : len(COLUMNS)].copy()
    raw.columns = COLUMNS[: raw.shape[1]]
    kept = raw[raw["status"].isin(KEPT_STATUS)].copy()
    kept.attrs["rows_dropped"] = int(len(raw) - len(kept))
    kept["date"] = pd.to_datetime(kept["datum"].astype(str).str[:10], errors="coerce").dt.date
    kept["time"] = kept["datum"].astype(str).str[11:16]
    kept["prefix"] = kept["prefix"].astype("string").str.strip().str.upper()
    for name in ("platser", "anmalda"):
        kept[name] = pd.to_numeric(kept[name], errors="coerce")
    return kept


def reconcile(occasions: pd.DataFrame, bookings: pd.DataFrame, ladok_activities: pd.DataFrame) -> dict[str, Any]:
    """Coverage per month and the match against bookings (prefix and date) and against the existing extract (course, date, time)."""
    bookings = bookings.copy()
    bookings["date"] = pd.to_datetime(bookings["scheduled_date"], errors="coerce").dt.date
    bookings = bookings[bookings["date"].notna()]
    booked = {(str(prefix).upper(), day) for prefix, day in zip(bookings["prefix"], bookings["date"]) if pd.notna(prefix)}
    listed = {(prefix, day) for prefix, day in zip(occasions["prefix"], occasions["date"]) if pd.notna(prefix) and pd.notna(day)}
    months: dict[str, dict[str, int]] = {}
    for key in booked:
        row = months.setdefault(key[1].strftime("%Y-%m"), {"booked_exam_days": 0, "matched_by_prefix_and_date": 0})
        row["booked_exam_days"] += 1
        row["matched_by_prefix_and_date"] += int(key in listed)
    existing = ladok_activities.copy()
    existing["key_date"] = existing["start_date"].astype(str).str[:10]
    existing["key_time"] = existing["start_time"].astype(str).str[:5]
    own = occasions.assign(key_date=occasions["datum"].astype(str).str[:10], key_time=occasions["time"])
    joined = existing.merge(own, left_on=["course_code", "key_date", "key_time"], right_on=["kurskod", "key_date", "key_time"], how="inner")
    comparable = joined[joined["anmalda"].notna() & joined["registered_count"].notna()]
    month_counts = occasions["date"].map(lambda day: day.strftime("%Y-%m") if pd.notna(day) else None).value_counts().sort_index()
    return {
        "occasions": int(len(occasions)), "rows_dropped": int(occasions.attrs.get("rows_dropped", 0)),
        "first_date": str(min(occasions["date"].dropna())), "last_date": str(max(occasions["date"].dropna())),
        "occasions_per_month": {str(month): int(count) for month, count in month_counts.items()},
        "occasions_without_prefix": int(occasions["prefix"].isna().sum()), "occasions_without_registered": int(occasions["anmalda"].isna().sum()),
        "occasions_without_places": int(occasions["platser"].isna().sum()),
        "existing_extract": {"rows": int(len(existing)), "months": {str(k): int(v) for k, v in existing["key_date"].str[:7].value_counts().sort_index().items()},
                             "joined_on_course_date_time": int(len(joined)),
                             "registered_equal": int((comparable["anmalda"] == comparable["registered_count"]).sum()), "comparable_rows": int(len(comparable))},
        "booked_exam_days_by_month": dict(sorted(months.items())),
        "note": "Mätning av täckning och koppling; ingen efterfrågan skrivs. Kurskoden i listan stämmer ofta inte med kurskoden i uttaget, så kopplingen mot bokningar görs på prefix och datum.",
    }


def main(argv: list[str]) -> int:
    from .paths import REPO_ROOT, SourceFiles, default_source_dir

    source_dir = Path(argv[0]) if argv else default_source_dir()
    processed = Path(argv[1]) if len(argv) > 1 else REPO_ROOT / "data" / "processed"
    occasions = load_occasions(source_dir / "Ladok ALLA aktivitetstillfällen 1 jan 31 jul.xlsx")
    result = reconcile(occasions, pd.read_csv(processed / "bookings.csv", encoding="utf-8-sig"),
                       pd.read_csv(processed / "ladok_activities.csv", encoding="utf-8-sig"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
