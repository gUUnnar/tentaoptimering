"""Route for the reported attendance (`/api/attendance`): a read-only summary of the prepared attendance file.

Attendance is observed use, not demand. It is read from `attendance.csv` of the prepared underlay and never starts a run;
without the file the route says so instead of returning zeros.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from fastapi import FastAPI

from .app_storage import AppStorage
from .attendance import ATTENDANCE_FILE, QUALITY_FILE, attendance_summary


def attendance_payload(processed_dir) -> dict[str, Any]:
    path = processed_dir / ATTENDANCE_FILE
    quality_path = processed_dir / QUALITY_FILE
    quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.is_file() else None
    if not path.is_file():
        if quality and quality.get("error"):  # the file was given but could not be read
            return {"available": False, "quality": quality, "note": quality["error"]}
        return {"available": False, "note": "Närvarouppföljningen är inte förberedd. Lägg filen bland källfilerna och förbered underlaget igen."}
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame["attendance_above_places"] = frame["attendance_above_places"].astype(bool)
    frame["at_fyrishov"] = frame["at_fyrishov"].astype(bool)
    return {"available": True, "summary": attendance_summary(frame), "quality": quality,
            "kind": "observed_attendance", "note": "Rapporterad närvaro är observerad användning och inte dimensionerande efterfrågan."}


def register_attendance_routes(app: FastAPI, storage: AppStorage) -> None:
    @app.get("/api/attendance")
    def attendance() -> dict[str, Any]:
        """Attendance against adjusted places by month and exam type, with data-quality counts."""
        return attendance_payload(storage.processed_dir)
