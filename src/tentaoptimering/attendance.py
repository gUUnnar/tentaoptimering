"""Reported attendance (närvarouppföljning) as its own data grain, never as demand.

The follow-up file says how many students actually sat each exam. It is *observed attendance*, not the number of seats that
had to be available: it is used to show the gap between booked places and use, and as documented support for the planning
share parameters (`demand.planning_share_*`). It is not linked to a booked room or to the demand of the model; the
location text is kept as written (a street address, a building or "Fyrishov"), and a missing value stays missing, never zero.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

SHEET = "Tentor"
ATTENDANCE_FILE = "attendance.csv"
QUALITY_FILE = "attendance_quality.json"

# output column -> start of the source column name (the source names contain Swedish characters and trailing spaces)
_SOURCE = {
    "course_code": "Kurskoder", "status": "Status", "course_name": "Kursnamn", "scheduled_date": "Inbokat datum",
    "scheduled_time": "Inbokad tid", "day_part": "FM/EM", "location_text": "Skrivsal", "exam_type": "Typ av tenta",
    "initial_places": "Initial", "placed_places": "Placerad ord", "adjusted_places": "Justerat tot",
    "attendance": "Närvaro", "absent": "Frånvaro", "registered_ladok": "Anmälda Ladok",
}
_NUMBERS = ("initial_places", "placed_places", "adjusted_places", "attendance", "absent", "registered_ladok")
COLUMNS = list(_SOURCE) + ["month", "source_row", "attendance_share", "attendance_above_places", "at_fyrishov", "status_is_date"]


def load_attendance(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None)
    frame = sheets.get(SHEET)
    if frame is None:
        frame = next(iter(sheets.values()))
    frame = frame.copy()
    frame.columns = [str(name).strip() for name in frame.columns]
    return frame


def normalize_attendance(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """The attendance rows in a stable layout plus a quality record: duplicates, impossible values and what could not be read."""
    duplicate_mask = raw.duplicated()  # identical in every source column; rows that differ anywhere are kept
    duplicates = int(duplicate_mask.sum())
    rows_read = len(raw)
    raw = raw[~duplicate_mask]
    columns = {}
    for target, prefix in _SOURCE.items():
        found = next((name for name in raw.columns if str(name).startswith(prefix)), None)
        columns[target] = raw[found] if found is not None else pd.Series([None] * len(raw), index=raw.index)
    frame = pd.DataFrame(columns)
    frame["source_row"] = [index + 2 for index in raw.index]  # the spreadsheet row, header on row 1
    parsed = pd.to_datetime(frame["scheduled_date"], errors="coerce")
    undated = int(parsed.isna().sum())
    frame["scheduled_date"] = parsed.dt.date.astype("string")
    frame["month"] = parsed.dt.strftime("%Y-%m")
    for name in _NUMBERS:
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    for name in ("course_code", "status", "course_name", "scheduled_time", "day_part", "location_text", "exam_type"):
        frame[name] = frame[name].astype("string").str.strip()
    frame["attendance_share"] = (frame["attendance"] / frame["adjusted_places"]).where(frame["adjusted_places"] > 0)
    frame["attendance_above_places"] = frame["attendance"] > frame["adjusted_places"]
    frame["at_fyrishov"] = frame["location_text"].str.contains("fyrishov", case=False, na=False)
    frame["status_is_date"] = pd.to_datetime(frame["status"], errors="coerce", format="mixed").notna() & ~frame["status"].isin(["Klar", "Avbokad"])
    frame = frame[COLUMNS].reset_index(drop=True)
    dated = frame[frame["scheduled_date"].notna()]
    quality = {
        "rows_read": int(rows_read), "duplicate_rows_removed": duplicates, "rows": int(len(frame)), "rows_without_date": undated,
        "first_date": str(dated["scheduled_date"].min()) if len(dated) else None, "last_date": str(dated["scheduled_date"].max()) if len(dated) else None,
        "rows_without_attendance": int(frame["attendance"].isna().sum()), "rows_without_places": int(frame["adjusted_places"].isna().sum()),
        "rows_attendance_above_adjusted_places": int(frame["attendance_above_places"].sum()),
        "rows_with_date_in_status": int(frame["status_is_date"].sum()),
        "location_unspecific_rows": int((frame["location_text"].isna() | frame["location_text"].str.fullmatch(r"\s*", na=False)).sum()),
        "note": "Rapporterad närvaro är observerad användning, inte dimensionerande efterfrågan. Den är inte kopplad till en bokad sal; saknade värden är okända, aldrig noll.",
    }
    return frame, quality


def attendance_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """Attendance against adjusted places per month and exam type, with the total and the share at Fyrishov.

    Rows without attendance or places are left out of every share (an unknown is not a zero); `attendance_above_places`
    rows are kept and counted, since a share above 100 % is a data question that the summary must not hide.
    """
    usable = frame[frame["attendance"].notna() & (frame["adjusted_places"] > 0)]

    def block(part: pd.DataFrame) -> dict[str, Any]:
        places = float(part["adjusted_places"].sum())
        return {"rows": int(len(part)), "attendance": int(part["attendance"].sum()), "adjusted_places": int(places),
                "share": round(float(part["attendance"].sum()) / places, 4) if places else None,
                "rows_above_places": int(part["attendance_above_places"].sum())}

    by_month_type = [
        {"month": str(month), "exam_type": str(kind), **block(part)}
        for (month, kind), part in usable.groupby(["month", "exam_type"], dropna=False)
    ]
    return {"total": block(usable), "at_fyrishov": block(usable[usable["at_fyrishov"]]), "elsewhere": block(usable[~usable["at_fyrishov"]]),
            "by_month_and_type": by_month_type, "rows_unusable": int(len(frame) - len(usable))}
