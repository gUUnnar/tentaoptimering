from __future__ import annotations

from pathlib import Path

import pandas as pd


BOOKING_COLUMNS = [
    "org_code",
    "course_codes",
    "prefix",
    "status",
    "course_name",
    "co_exam",
    "co_exam_identical",
    "co_exam_comment",
    "scheduled_date",
    "weekday",
    "scheduled_time",
    "duration",
    "day_part",
    "address",
    "room",
    "booked_places",
    "candidate_count",
    "original_candidate_count",
    "re_exam_candidates",
    "support_candidates",
    "support_placed",
    "requested_date",
    "reserve_date_1",
    "reserve_date_2",
    "no_reserve_date_reason",
    "exam_type",
    "digital_exam",
    "exam_name",
    "city",
    "transport",
    "transport_comment",
    "depot",
    "coordination_comment",
    "institution_comment",
    "raindance_project",
]

LADOK_COLUMNS = [
    "course_code",
    "name_sv",
    "start_date",
    "start_time",
    "activity_type",
    "location",
    "registration_flag",
    "total_count",
    "registered_count",
    "cancelled_count",
    "added_count",
    "re_registered_or_early_term_count",
]

LEASE_COLUMNS = [
    "tenant_name",
    "org_code",
    "lease_object",
    "valid_from",
    "valid_to",
    "building_name",
    "floor",
    "room",
    "total_area_sqm",
    "own_area_sqm",
    "annual_internal_rent_prelim_2026_sek",
    "cleaned_by_uu",
    "landlord",
]


def _assert_width(frame: pd.DataFrame, expected: list[str], source: Path) -> pd.DataFrame:
    if frame.shape[1] != len(expected):
        raise ValueError(
            f"Oväntat antal kolumner i {source.name}: {frame.shape[1]} i stället för "
            f"{len(expected)}. Källschemat behöver granskas."
        )
    result = frame.copy()
    result.columns = expected
    return result


def load_bookings(path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name="Data i systemet")
    return _assert_width(frame, BOOKING_COLUMNS, path)


def load_ladok(path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name=0)
    return _assert_width(frame, LADOK_COLUMNS, path)


def load_leases(path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name="Rapport", header=4)
    return _assert_width(frame, LEASE_COLUMNS, path)
