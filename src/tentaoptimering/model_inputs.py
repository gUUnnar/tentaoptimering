from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any

import pandas as pd

from .linkage import booking_start_time, extract_course_codes


DEMAND_COLUMNS = {
    "total_count",
    "registered_count",
    "cancelled_count",
    "added_count",
    "re_registered_or_early_term_count",
}


@dataclass(frozen=True)
class OptimizationInputs:
    exam_events: pd.DataFrame
    activity_booking_candidates: pd.DataFrame
    room_inventory: pd.DataFrame
    optimization_rooms: pd.DataFrame
    optimization_demands: pd.DataFrame
    optimization_placements: pd.DataFrame
    metrics: dict[str, Any]


@dataclass(frozen=True)
class PocPolicy:
    allow_current_published_room_capacity: bool
    room_availability_mode: str


def load_demand_measure(parameter_path: Path) -> str:
    """Read the provisional demand field from the machine-readable registry."""
    payload = tomllib.loads(parameter_path.read_text(encoding="utf-8"))
    for parameter in payload["parameter"]:
        if parameter["id"] == "demand_measure":
            field = parameter.get("source_field")
            if field in DEMAND_COLUMNS:
                return field
    raise ValueError("Parameterregistret saknar ett giltigt source_field för demand_measure.")


def load_poc_policy(parameter_path: Path) -> PocPolicy:
    """Read the explicitly authorized exploratory assumptions from the registry."""
    payload = tomllib.loads(parameter_path.read_text(encoding="utf-8"))
    parameters = {item["id"]: item for item in payload["parameter"]}
    inventory = parameters.get("allowed_room_inventory", {})
    availability = parameters.get("poc_room_availability_mode", {})
    mode = availability.get("value")
    if not isinstance(mode, str) or not mode:
        raise ValueError("Parameterregistret saknar poc_room_availability_mode.value.")
    return PocPolicy(
        allow_current_published_room_capacity=inventory.get("enabled") is True,
        room_availability_mode=mode,
    )


def load_room_register(path: Path) -> pd.DataFrame:
    """Load the versioned public room reference without inferring missing values."""
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for room in payload["room"]:
        records.append(
            {
                "reference_room_id": room["reference_room_id"],
                "location_key": room["booking_location_key"],
                "reference_room_key": room.get("booking_room_key"),
                "reference_address": room["address"],
                "reference_room_name": room["room_name"],
                "reference_city": room["city"],
                "capacity_seats": room.get("capacity_seats"),
                "capacity_scope": room["capacity_scope"],
                "published_availability_context": room["published_availability_context"],
                "digital_capability_status": room["digital_capability_status"],
                "accessibility_status": room["accessibility_status"],
                "special_support_status": room["special_support_status"],
                "reference_source_url": payload["source_url"],
                "reference_source_last_updated": payload["source_last_updated"],
                "capacity_temporal_status": payload["temporal_status"],
                "source_published_total_places": payload["published_total_places"],
                "source_published_address_count": payload["published_address_count"],
                "source_published_exam_room_count": payload["published_exam_room_count"],
            }
        )
    result = pd.DataFrame.from_records(records)
    result["capacity_seats"] = pd.to_numeric(result["capacity_seats"], errors="coerce").astype(
        "Int64"
    )
    return result


def _distinct_text(series: pd.Series) -> str | None:
    values = sorted({str(value) for value in series.dropna() if str(value).strip()})
    return " | ".join(values) if values else None


def _build_exam_events(bookings: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    placements = bookings.copy()
    for optional_column in ("support_placed", "digital_exam", "exam_type"):
        if optional_column not in placements:
            placements[optional_column] = pd.NA
    placements["booking_start_time"] = placements["scheduled_time"].map(booking_start_time)
    event_keys = ["exam_order_id", "scheduled_date", "scheduled_time"]
    events = (
        placements.groupby(event_keys, dropna=False, sort=True)
        .agg(
            placement_count=("placement_id", "size"),
            booking_statuses=("status", _distinct_text),
            observed_booked_places_total=("booked_places", "sum"),
            observed_booked_places_max=("booked_places", "max"),
            observed_cities=("city", _distinct_text),
            observed_support_placed_max=("support_placed", "max"),
            observed_digital_exam_values=("digital_exam", _distinct_text),
            observed_exam_types=("exam_type", _distinct_text),
        )
        .reset_index()
    )
    events.insert(0, "exam_event_id", [f"exam-event-{index:07d}" for index in range(1, len(events) + 1)])
    placements = placements.merge(events[event_keys + ["exam_event_id"]], on=event_keys, how="left")
    event_courses = placements.loc[
        :, ["exam_event_id", "scheduled_date", "booking_start_time", "course_codes"]
    ].copy()
    event_courses["course_code"] = event_courses["course_codes"].map(extract_course_codes)
    event_courses = event_courses.explode("course_code", ignore_index=True).dropna(
        subset=["course_code", "scheduled_date", "booking_start_time"]
    )
    event_courses = event_courses.drop(columns="course_codes").drop_duplicates()
    return events, placements, event_courses


def _build_candidate_relations(
    ladok: pd.DataFrame, event_courses: pd.DataFrame, demand_column: str
) -> pd.DataFrame:
    key_columns = ["course_code", "scheduled_date", "booking_start_time"]
    activities = ladok.loc[:, ["activity_id", "course_code", "start_date", "start_time", demand_column]].copy()
    activities = activities.rename(
        columns={"start_date": "scheduled_date", "start_time": "booking_start_time"}
    ).dropna(subset=key_columns)
    activities = activities.rename(columns={demand_column: "demand_value"})
    event_courses = event_courses.loc[:, ["exam_event_id", *key_columns]].copy()

    activity_counts = activities.groupby(key_columns, dropna=False)["activity_id"].size()
    event_counts = event_courses.groupby(key_columns, dropna=False)["exam_event_id"].size()
    relations = activities.merge(event_courses, on=key_columns, how="outer", indicator=True)
    relation_index = pd.MultiIndex.from_frame(relations[key_columns])
    relations["ladok_activity_candidate_count"] = relation_index.map(activity_counts).fillna(0).astype("Int64")
    relations["exam_event_candidate_count"] = relation_index.map(event_counts).fillna(0).astype("Int64")

    def relationship_status(row: pd.Series) -> str:
        if row["_merge"] == "left_only":
            return "no_booking_candidate"
        if row["_merge"] == "right_only":
            return "no_ladok_candidate"
        if row["ladok_activity_candidate_count"] == 1 and row["exam_event_candidate_count"] == 1:
            return "unambiguous_candidate"
        return "ambiguous_candidates"

    relations["relationship_status"] = relations.apply(relationship_status, axis=1)
    relations["demand_measure_source_field"] = demand_column
    relations["demand_input_status"] = "not_selected_for_optimization"
    selected = relations["relationship_status"].eq("unambiguous_candidate")
    relations.loc[selected & relations["demand_value"].notna(), "demand_input_status"] = (
        "ready_provisional_ladok_demand"
    )
    relations.loc[selected & relations["demand_value"].isna(), "demand_input_status"] = (
        "missing_configured_demand_value"
    )
    return relations.drop(columns="_merge")


def _build_room_inventory(
    placements: pd.DataFrame, leases: pd.DataFrame, official_rooms: pd.DataFrame
) -> pd.DataFrame:
    grouped = (
        placements.groupby("location_key", dropna=False, sort=True)
        .agg(
            observed_addresses=("address", _distinct_text),
            observed_room_names=("room", _distinct_text),
            observed_cities=("city", _distinct_text),
            observed_placement_count=("placement_id", "size"),
            observed_booked_places_max=("booked_places", "max"),
            first_observed_date=("scheduled_date", "min"),
            last_observed_date=("scheduled_date", "max"),
            room_key=("room_key", "first"),
        )
        .reset_index()
    )
    grouped["observed_in_booking_period"] = True
    grouped = grouped.merge(official_rooms, on="location_key", how="outer", validate="one_to_one")
    grouped["observed_in_booking_period"] = grouped["observed_in_booking_period"].fillna(False)
    grouped["room_key"] = grouped["room_key"].fillna(grouped["reference_room_key"])
    grouped.insert(0, "room_id", grouped["reference_room_id"].astype("string"))
    observed_identity = grouped["observed_addresses"].notna() & grouped["observed_room_names"].notna()
    derived_identity = grouped["room_id"].isna() & observed_identity
    grouped.loc[derived_identity, "room_id"] = grouped.loc[derived_identity, "location_key"].map(
        lambda value: f"derived-{str(value).replace('|', '-')}"
    )
    grouped["room_identity_status"] = "not_identified_missing_address_or_room"
    grouped.loc[derived_identity, "room_identity_status"] = "identified_from_booking_only"
    grouped.loc[
        grouped["reference_room_id"].notna() & grouped["observed_in_booking_period"].eq(False),
        "room_identity_status",
    ] = "official_reference_not_observed_in_booking_period"
    grouped.loc[
        grouped["reference_room_id"].notna() & grouped["observed_in_booking_period"],
        "room_identity_status",
    ] = "matched_official_reference_and_booking"
    published_room_capacity = grouped["capacity_seats"].notna() & grouped["capacity_scope"].eq("room")
    published_facility_capacity = grouped["capacity_seats"].notna() & grouped["capacity_scope"].ne("room")
    grouped["capacity_status"] = "missing_no_published_room_capacity"
    grouped.loc[published_room_capacity, "capacity_status"] = (
        "official_published_current_not_verified_for_booking_period"
    )
    grouped.loc[published_facility_capacity, "capacity_status"] = (
        "official_facility_total_not_individual_room_capacity"
    )
    grouped["capacity_usable_for_booking_period"] = False
    grouped["availability_status"] = grouped["reference_room_id"].notna().map(
        {
            True: "official_current_not_verified_for_booking_period",
            False: "missing_no_verified_room_availability_source",
        }
    )
    grouped["digital_capability_status"] = grouped["digital_capability_status"].fillna(
        "not_inferred_from_exam_booking"
    )
    grouped["accessibility_status"] = grouped["accessibility_status"].fillna(
        "not_stated_in_available_sources"
    )
    grouped["special_support_status"] = grouped["special_support_status"].fillna(
        "not_inferred_from_support_placements"
    )
    lease_counts = leases["room_key"].value_counts(dropna=True)
    grouped["lease_room_name_candidate_count"] = grouped["room_key"].map(lease_counts).fillna(0).astype("Int64")
    grouped["lease_link_status"] = grouped["lease_room_name_candidate_count"].map(
        {0: "no_room_name_candidate", 1: "unverified_room_name_only"}
    ).fillna("unverified_multiple_room_name_candidates")
    return grouped.drop(columns=["room_key", "reference_room_key"])


def _build_optimization_rooms(rooms: pd.DataFrame, policy: PocPolicy) -> pd.DataFrame:
    """Select only room-scoped published capacities for an exploratory scenario."""
    published_room_capacity = rooms["capacity_seats"].notna() & rooms["capacity_scope"].eq("room")
    result = rooms.loc[
        published_room_capacity,
        [
            "room_id",
            "reference_address",
            "reference_room_name",
            "reference_city",
            "capacity_seats",
            "capacity_status",
            "capacity_temporal_status",
            "published_availability_context",
            "digital_capability_status",
            "accessibility_status",
            "special_support_status",
            "observed_in_booking_period",
            "reference_source_url",
            "reference_source_last_updated",
        ],
    ].copy()
    result["capacity_input_status"] = "excluded_poc_policy_not_enabled"
    if policy.allow_current_published_room_capacity:
        result["capacity_input_status"] = "ready_exploratory_poc_public_capacity"
    result["eligible_for_exploratory_capacity_poc"] = (
        policy.allow_current_published_room_capacity
    )
    result["availability_input_status"] = policy.room_availability_mode
    result["eligible_for_operational_scheduling"] = False
    result["operational_exclusion_reason"] = (
        "missing_verified_calendar_availability_and_capacity_validity"
    )
    return result


def build_optimization_inputs(
    bookings: pd.DataFrame,
    ladok: pd.DataFrame,
    leases: pd.DataFrame,
    demand_column: str,
    official_rooms: pd.DataFrame | None = None,
    poc_policy: PocPolicy | None = None,
) -> OptimizationInputs:
    """Create traceable inputs while retaining all unresolved source ambiguity."""
    if demand_column not in DEMAND_COLUMNS:
        raise ValueError(f"Okänt Ladokfält för efterfrågan: {demand_column}")
    if poc_policy is None:
        poc_policy = PocPolicy(False, "not_configured")
    events, placements, event_courses = _build_exam_events(bookings)
    candidates = _build_candidate_relations(ladok, event_courses, demand_column)
    if official_rooms is None:
        official_rooms = pd.DataFrame(
            columns=[
                "reference_room_id",
                "location_key",
                "reference_room_key",
                "reference_address",
                "reference_room_name",
                "reference_city",
                "capacity_seats",
                "capacity_scope",
                "published_availability_context",
                "digital_capability_status",
                "accessibility_status",
                "special_support_status",
                "reference_source_url",
                "reference_source_last_updated",
                "capacity_temporal_status",
                "source_published_total_places",
                "source_published_address_count",
                "source_published_exam_room_count",
            ]
        )
    rooms = _build_room_inventory(placements, leases, official_rooms)
    optimization_rooms = _build_optimization_rooms(rooms, poc_policy)
    demands = candidates.loc[
        candidates["relationship_status"].eq("unambiguous_candidate"),
        [
            "activity_id",
            "exam_event_id",
            "course_code",
            "scheduled_date",
            "booking_start_time",
            "demand_value",
            "demand_measure_source_field",
            "demand_input_status",
        ],
    ].copy()
    demands.insert(0, "demand_id", demands["activity_id"])
    demands = demands.merge(
        events.loc[
            :,
            [
                "exam_event_id",
                "scheduled_time",
                "observed_cities",
                "observed_support_placed_max",
                "observed_digital_exam_values",
                "observed_exam_types",
            ],
        ],
        on="exam_event_id",
        how="left",
        validate="many_to_one",
    )
    room_lookup = rooms.loc[
        :,
        [
            "location_key",
            "room_id",
            "room_identity_status",
            "capacity_seats",
            "capacity_scope",
            "capacity_status",
            "capacity_usable_for_booking_period",
        ],
    ]
    optimization_placements = demands.loc[:, ["demand_id", "exam_event_id"]].merge(
        placements.loc[:, ["placement_id", "exam_event_id", "location_key", "booked_places"]],
        on="exam_event_id",
        how="left",
        validate="many_to_many",
    ).merge(room_lookup, on="location_key", how="left", validate="many_to_one")
    optimization_placements["room_assignment_status"] = "room_not_identified"
    observed_only = optimization_placements["room_id"].notna()
    optimization_placements.loc[observed_only, "room_assignment_status"] = (
        "observed_location_without_published_room_capacity"
    )
    facility_reference = optimization_placements["capacity_seats"].notna() & optimization_placements[
        "capacity_scope"
    ].ne("room")
    optimization_placements.loc[facility_reference, "room_assignment_status"] = (
        "facility_total_not_individual_room_capacity"
    )
    room_reference = optimization_placements["capacity_seats"].notna() & optimization_placements[
        "capacity_scope"
    ].eq("room")
    optimization_placements.loc[room_reference, "room_assignment_status"] = (
        "published_room_capacity_not_verified_for_booking_period"
    )
    activity_status = candidates.loc[candidates["activity_id"].notna()].drop_duplicates("activity_id")
    ready_demands = demands["demand_input_status"].eq("ready_provisional_ladok_demand")
    available_ladok_demand = ladok[demand_column].dropna()
    ready_demand_sum = int(demands.loc[ready_demands, "demand_value"].sum())
    identified_demand_count = int(
        optimization_placements.loc[optimization_placements["room_id"].notna(), "demand_id"].nunique()
    )
    published_room_demand_count = int(
        optimization_placements.loc[
            optimization_placements["room_assignment_status"].eq(
                "published_room_capacity_not_verified_for_booking_period"
            ),
            "demand_id",
        ].nunique()
    )
    published_room_capacity = rooms["capacity_seats"].notna() & rooms["capacity_scope"].eq("room")
    poc_ready_rooms = optimization_rooms["eligible_for_exploratory_capacity_poc"]
    published_total_places = rooms["source_published_total_places"].dropna()
    listed_capacity_sum = int(rooms["capacity_seats"].sum())
    metrics = {
        "demand_measure_source_field": demand_column,
        "booking_exam_events": int(len(events)),
        "ladok_activities_total": int(len(ladok)),
        "ladok_activities_with_candidate_key": int(len(activity_status)),
        "ladok_activities_without_candidate_key": int(len(ladok) - len(activity_status)),
        "ladok_activities_unambiguous_candidate": int(
            activity_status["relationship_status"].eq("unambiguous_candidate").sum()
        ),
        "ladok_activity_candidate_coverage_percent": round(
            100
            * activity_status["relationship_status"].eq("unambiguous_candidate").sum()
            / len(ladok),
            1,
        ) if len(ladok) else None,
        "ladok_activities_ambiguous_candidates": int(
            activity_status["relationship_status"].eq("ambiguous_candidates").sum()
        ),
        "ladok_activities_without_booking_candidate": int(
            activity_status["relationship_status"].eq("no_booking_candidate").sum()
        ),
        "optimization_demands_ready_provisional": int(ready_demands.sum()),
        "optimization_demand_record_coverage_percent": round(
            100 * ready_demands.sum() / len(ladok), 1
        ) if len(ladok) else None,
        "optimization_demands_missing_configured_value": int((~ready_demands).sum()),
        "optimization_demand_sum_ready_provisional": ready_demand_sum,
        "available_ladok_demand_sum": int(available_ladok_demand.sum()),
        "available_ladok_demand_share_in_ready_inputs_percent": round(
            100 * ready_demand_sum / available_ladok_demand.sum(), 1
        ) if not available_ladok_demand.empty and available_ladok_demand.sum() else None,
        "optimization_placements": int(len(optimization_placements)),
        "observed_booking_locations": int(rooms["observed_in_booking_period"].sum()),
        "published_room_reference_entries": int(rooms["reference_room_id"].notna().sum()),
        "published_room_capacities": int(published_room_capacity.sum()),
        "published_total_places_claim": (
            int(published_total_places.iloc[0]) if not published_total_places.empty else None
        ),
        "sum_of_individually_listed_capacities": listed_capacity_sum,
        "published_capacity_reconciliation_gap": (
            int(published_total_places.iloc[0]) - listed_capacity_sum
            if not published_total_places.empty
            else None
        ),
        "observed_rooms_with_published_capacity": int(
            (published_room_capacity & rooms["observed_in_booking_period"]).sum()
        ),
        "rooms_with_verified_capacity": int(rooms["capacity_usable_for_booking_period"].sum()),
        "poc_policy_allows_current_published_capacity": (
            poc_policy.allow_current_published_room_capacity
        ),
        "optimization_rooms_ready_for_exploratory_poc": int(poc_ready_rooms.sum()),
        "optimization_room_capacity_sum_ready_for_exploratory_poc": int(
            optimization_rooms.loc[poc_ready_rooms, "capacity_seats"].sum()
        ),
        "poc_room_availability_mode": poc_policy.room_availability_mode,
        "capacity_optimization_readiness": (
            "ready_for_exploratory_capacity_poc_with_explicit_uncertainty"
            if poc_ready_rooms.any() and ready_demands.any()
            else "blocked_missing_poc_room_capacity_or_demand"
        ),
        "operational_scheduling_readiness": (
            "blocked_missing_verified_availability_and_business_rules"
        ),
        "economic_savings_readiness": "blocked_missing_verified_cost_avoidability",
        "demands_with_any_identified_booking_room": identified_demand_count,
        "demands_with_published_room_capacity_reference": published_room_demand_count,
        "ready_demands_with_published_room_capacity_reference_percent": round(
            100 * published_room_demand_count / ready_demands.sum(), 1
        ) if ready_demands.sum() else None,
        "ready_demands_with_any_identified_booking_room_percent": round(
            100 * identified_demand_count / ready_demands.sum(), 1
        ) if ready_demands.sum() else None,
    }
    return OptimizationInputs(
        events,
        candidates,
        rooms,
        optimization_rooms,
        demands,
        optimization_placements,
        metrics,
    )
