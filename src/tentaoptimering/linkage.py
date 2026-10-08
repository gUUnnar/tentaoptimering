from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import pandas as pd


COURSE_CODE_PATTERN = re.compile(r"(?<![0-9A-ZÅÄÖ])[0-9A-ZÅÄÖ]{6}(?![0-9A-ZÅÄÖ])")
TIME_PATTERN = re.compile(r"(\d{1,2}):(\d{2})")


@dataclass(frozen=True)
class CandidateLinkageResult:
    """Diagnostic candidate links, never a verified booking-to-activity join."""

    metrics: dict[str, Any]
    candidate_links: pd.DataFrame


def extract_course_codes(value: object) -> list[str]:
    """Extract distinct six-character course codes from a booking export cell."""
    if value is None or pd.isna(value):
        return []
    matches = COURSE_CODE_PATTERN.findall(str(value).upper())
    return list(dict.fromkeys(matches))


def booking_start_time(value: object) -> str | None:
    """Take the first clock time from a booking interval for candidate comparison."""
    if value is None or pd.isna(value):
        return None
    match = TIME_PATTERN.search(str(value))
    if not match:
        return None
    hour, minute = match.groups()
    return f"{int(hour):02d}:{minute}"


def candidate_linkage(bookings: pd.DataFrame, ladok: pd.DataFrame) -> CandidateLinkageResult:
    """Measure candidate linkage without asserting that any pair is a true match.

    Course code, date and start time are evidence fields shared by the sources. They
    are deliberately not promoted to a primary key: co-exams, several room
    placements and repeated Ladok activity keys remain visible as ambiguity.
    """
    booking_candidates = bookings.loc[
        :, [
            "placement_id",
            "exam_order_id",
            "course_codes",
            "scheduled_date",
            "scheduled_time",
            "location_key",
        ]
    ].copy()
    booking_candidates["course_code"] = booking_candidates["course_codes"].map(extract_course_codes)
    booking_candidates["booking_start_time"] = booking_candidates["scheduled_time"].map(
        booking_start_time
    )
    booking_candidates = booking_candidates.explode("course_code", ignore_index=True)
    booking_candidates = booking_candidates.dropna(
        subset=["course_code", "scheduled_date", "booking_start_time"]
    ).drop(columns="course_codes")

    activity_candidates = ladok.loc[
        :, ["activity_id", "course_code", "start_date", "start_time", "location_key"]
    ].copy()
    activity_candidates = activity_candidates.dropna(
        subset=["course_code", "start_date", "start_time"]
    ).rename(
        columns={
            "start_date": "scheduled_date",
            "start_time": "booking_start_time",
            "location_key": "activity_location_key",
        }
    )

    key_columns = ["course_code", "scheduled_date", "booking_start_time"]
    activity_counts = activity_candidates.groupby(key_columns, dropna=False)["activity_id"].size()
    candidate_links = booking_candidates.merge(
        activity_candidates,
        how="left",
        on=key_columns,
        validate="many_to_many",
    ).rename(columns={"location_key": "booking_location_key"})
    candidate_links["candidate_activity_count"] = pd.MultiIndex.from_frame(
        candidate_links[key_columns]
    ).map(activity_counts).fillna(0).astype("Int64")
    candidate_links["candidate_status"] = candidate_links["candidate_activity_count"].map(
        {0: "no_candidate", 1: "single_candidate"}
    ).fillna("ambiguous_candidates")
    candidate_links["location_key_equal"] = (
        candidate_links["booking_location_key"].notna()
        & candidate_links["activity_location_key"].notna()
        & candidate_links["booking_location_key"].eq(candidate_links["activity_location_key"])
    )

    distinct_booking_contexts = booking_candidates[key_columns].drop_duplicates()
    matched_context_index = set(activity_counts.index).intersection(
        set(pd.MultiIndex.from_frame(distinct_booking_contexts))
    )
    matched_activity_ids = set(
        candidate_links.loc[candidate_links["activity_id"].notna(), "activity_id"].astype(str)
    )
    # A physical placement can have several course codes (for example a co-exam).
    # Count its linkage state per placement and course code, not just per placement.
    row_status = candidate_links.drop_duplicates(["placement_id", "course_code"])
    booking_placements_with_course = int(booking_candidates["placement_id"].nunique())
    metrics = {
        "method": "candidate_key_course_code_scheduled_date_booking_start_time",
        "booking_placement_rows_total": int(len(bookings)),
        "booking_placement_rows_with_extractable_course_code": booking_placements_with_course,
        "booking_placement_rows_without_extractable_course_code": int(
            len(bookings) - booking_placements_with_course
        ),
        "booking_course_placement_rows_eligible": int(len(booking_candidates)),
        "booking_candidate_contexts": int(len(distinct_booking_contexts)),
        "booking_candidate_contexts_with_ladok_candidate": int(len(matched_context_index)),
        "booking_course_placement_rows_no_candidate": int(
            (row_status["candidate_status"] == "no_candidate").sum()
        ),
        "booking_course_placement_rows_single_candidate": int(
            (row_status["candidate_status"] == "single_candidate").sum()
        ),
        "booking_course_placement_rows_ambiguous_candidates": int(
            (row_status["candidate_status"] == "ambiguous_candidates").sum()
        ),
        "candidate_pairs": int(candidate_links["activity_id"].notna().sum()),
        "candidate_pairs_with_identical_location_key": int(
            candidate_links.loc[candidate_links["activity_id"].notna(), "location_key_equal"].sum()
        ),
        "ladok_activities_eligible": int(len(activity_candidates)),
        "ladok_activities_ineligible": int(len(ladok) - len(activity_candidates)),
        "ladok_activities_with_booking_candidate": int(len(matched_activity_ids)),
    }
    return CandidateLinkageResult(metrics=metrics, candidate_links=candidate_links)
