from __future__ import annotations

import re
import unicodedata

import pandas as pd


TEXT_COLUMNS_BOOKINGS = [
    "course_codes",
    "prefix",
    "status",
    "course_name",
    "co_exam",
    "co_exam_identical",
    "address",
    "room",
    "exam_type",
    "digital_exam",
    "exam_name",
    "city",
    "transport",
]


def clean_text(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    return text.mask(text.eq(""), pd.NA)


def key_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^0-9a-zåäö]+", "-", normalized)
    return normalized.strip("-") or None


def _date_strings(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d").astype("string")


def _time_strings(series: pd.Series) -> pd.Series:
    def convert(value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        match = re.search(r"(\d{1,2}):(\d{2})", str(value))
        return f"{int(match.group(1)):02d}:{match.group(2)}" if match else str(value).strip()

    return series.map(convert).astype("string")


def normalize_bookings(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in TEXT_COLUMNS_BOOKINGS:
        result[column] = clean_text(result[column])
    for column in ("scheduled_date", "requested_date", "reserve_date_1", "reserve_date_2"):
        result[column] = _date_strings(result[column])
    for column in (
        "booked_places",
        "candidate_count",
        "original_candidate_count",
        "re_exam_candidates",
        "support_candidates",
        "support_placed",
    ):
        result[column] = pd.to_numeric(result[column], errors="coerce").astype("Int64")

    result.insert(0, "placement_id", [f"placement-{index:07d}" for index in range(1, len(result) + 1)])
    prefix_key = result["prefix"].map(key_text).astype("string")
    missing_key = result["placement_id"].map(lambda value: f"missing-prefix-{value}")
    result.insert(1, "exam_order_id", prefix_key.fillna(missing_key))
    result["address_key"] = result["address"].map(key_text).astype("string")
    result["room_key"] = result["room"].map(key_text).astype("string")
    result["location_key"] = (
        result["address_key"].fillna("") + "|" + result["room_key"].fillna("")
    ).str.strip("|").replace("", pd.NA)
    return result


def normalize_ladok(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ("course_code", "name_sv", "activity_type", "location"):
        result[column] = clean_text(result[column])
    result["course_code"] = result["course_code"].str.upper()
    result["start_date"] = _date_strings(result["start_date"])
    result["start_time"] = _time_strings(result["start_time"])
    for column in (
        "registration_flag",
        "total_count",
        "registered_count",
        "cancelled_count",
        "added_count",
        "re_registered_or_early_term_count",
    ):
        result[column] = pd.to_numeric(result[column], errors="coerce").astype("Int64")
    result.insert(0, "activity_id", [f"ladok-{index:06d}" for index in range(1, len(result) + 1)])
    result["location_key"] = result["location"].map(key_text).astype("string")
    return result


def normalize_leases(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in (
        "tenant_name",
        "lease_object",
        "building_name",
        "floor",
        "room",
        "cleaned_by_uu",
        "landlord",
    ):
        result[column] = clean_text(result[column])
    for column in ("valid_from", "valid_to"):
        result[column] = _date_strings(result[column])
    for column in (
        "total_area_sqm",
        "own_area_sqm",
        "annual_internal_rent_prelim_2026_sek",
    ):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result.insert(0, "lease_row_id", [f"lease-row-{index:04d}" for index in range(1, len(result) + 1)])
    result["lease_object_key"] = result["lease_object"].map(key_text).astype("string")
    result["building_key"] = result["building_name"].map(key_text).astype("string")
    result["room_key"] = result["room"].map(key_text).astype("string")
    return result
