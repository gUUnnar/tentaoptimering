"""Canonical demand and scope accounting before operational optimization.

This module deliberately does not infer that a Ladok activity is an exam demand.
It makes every source activity visible, and requires an explicit membership through
a subgroup before participants can be summed into a canonical exam demand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


SCOPE_STATUSES = frozenset({"included", "excluded", "unresolved"})
SCOPE_COLUMNS = (
    "activity_id",
    "scope_status",
    "scope_reason_code",
    "evidence_reference",
)


@dataclass(frozen=True)
class ScopeReport:
    """A complete activity-level scope account, not an optimization input."""

    activities: pd.DataFrame
    metrics: dict[str, Any]


@dataclass(frozen=True)
class CanonicalDemandResult:
    """Validated relations from source activities to unique exam needs."""

    exam_demands: pd.DataFrame
    demand_subgroups: pd.DataFrame
    activity_scope: pd.DataFrame
    metrics: dict[str, Any]


def unresolved_scope_decisions(activities: pd.DataFrame) -> pd.DataFrame:
    """Create a full, honest initial scope register from a Ladok activity table."""
    _require_columns(activities, ("activity_id",), "Ladokaktiviteter")
    decisions = activities.loc[:, ["activity_id"]].copy()
    decisions["scope_status"] = "unresolved"
    decisions["scope_reason_code"] = "scope_not_assessed"
    decisions["evidence_reference"] = "missing_business_scope_decision"
    decisions["scope_decision_basis"] = "not_assessed"
    return decisions


def provisional_scope_decisions(
    activities: pd.DataFrame, activity_candidates: pd.DataFrame
) -> pd.DataFrame:
    """Classify technical readiness without claiming a business scope decision.

    The current exploratory subset is visible as ``included`` only for the named
    technical scope. All other activities remain unresolved rather than excluded.
    """
    decisions = unresolved_scope_decisions(activities)
    _require_columns(
        activity_candidates,
        ("activity_id", "relationship_status", "demand_input_status"),
        "aktivitetskandidater",
    )
    candidates = activity_candidates.dropna(subset=["activity_id"]).copy()
    candidates = candidates.drop_duplicates("activity_id")
    candidate_by_id = candidates.set_index("activity_id")
    for index, activity_id in decisions["activity_id"].items():
        if activity_id not in candidate_by_id.index:
            decisions.loc[index, "scope_reason_code"] = "no_technical_candidate_relation"
            decisions.loc[index, "evidence_reference"] = "activity_missing_from_candidate_relation"
            continue
        candidate = candidate_by_id.loc[activity_id]
        relationship = str(candidate["relationship_status"])
        input_status = str(candidate["demand_input_status"])
        decisions.loc[index, "scope_decision_basis"] = "technical_preparation"
        if relationship == "unambiguous_candidate" and input_status == "ready_provisional_ladok_demand":
            decisions.loc[index, "scope_status"] = "included"
            decisions.loc[index, "scope_reason_code"] = "exploratory_capacity_scope_candidate"
            decisions.loc[index, "evidence_reference"] = (
                "unambiguous_candidate_and_configured_provisional_demand"
            )
        elif relationship == "ambiguous_candidates":
            decisions.loc[index, "scope_reason_code"] = "ambiguous_activity_booking_relation"
            decisions.loc[index, "evidence_reference"] = "multiple_technical_candidates"
        elif relationship == "no_booking_candidate":
            decisions.loc[index, "scope_reason_code"] = "no_booking_candidate"
            decisions.loc[index, "evidence_reference"] = "no_matching_booking_event"
        elif input_status == "missing_configured_demand_value":
            decisions.loc[index, "scope_reason_code"] = "missing_configured_demand_value"
            decisions.loc[index, "evidence_reference"] = "unambiguous_candidate_missing_demand"
        else:
            decisions.loc[index, "scope_reason_code"] = "technical_scope_not_ready"
            decisions.loc[index, "evidence_reference"] = relationship
    return decisions


def build_scope_report(activities: pd.DataFrame, decisions: pd.DataFrame) -> ScopeReport:
    """Validate one documented scope decision for every source activity."""
    _require_columns(activities, ("activity_id",), "Ladokaktiviteter")
    _require_columns(decisions, SCOPE_COLUMNS, "scope-registret")
    source_ids = _unique_ids(activities["activity_id"], "Ladokaktiviteter")
    decision_ids = _unique_ids(decisions["activity_id"], "scope-registret")
    extra = decision_ids - source_ids
    missing = source_ids - decision_ids
    if extra:
        raise ValueError("Scope-registret innehåller okända activity_id: " + ", ".join(sorted(extra)))
    if missing:
        raise ValueError("Scope-beslut saknas för activity_id: " + ", ".join(sorted(missing)))
    invalid = set(decisions["scope_status"].dropna().astype(str)) - SCOPE_STATUSES
    if invalid or decisions["scope_status"].isna().any():
        raise ValueError("scope_status måste vara included, excluded eller unresolved.")
    for column in ("scope_reason_code", "evidence_reference"):
        if decisions[column].isna().any() or decisions[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"scope-registret saknar {column} för minst en aktivitet.")
    report = activities.merge(decisions, on="activity_id", how="left", validate="one_to_one")
    counts = report["scope_status"].value_counts().to_dict()
    metrics = {
        "source_activity_count": len(report),
        "included_activity_count": int(counts.get("included", 0)),
        "excluded_activity_count": int(counts.get("excluded", 0)),
        "unresolved_activity_count": int(counts.get("unresolved", 0)),
        "scope_complete_for_whole_population": counts.get("unresolved", 0) == 0,
    }
    if "scope_decision_basis" in report:
        metrics["scope_decision_basis_counts"] = report["scope_decision_basis"].value_counts().to_dict()
    return ScopeReport(report.sort_values("activity_id").reset_index(drop=True), metrics)


def build_canonical_exam_demands(
    activities: pd.DataFrame,
    decisions: pd.DataFrame,
    demand_definitions: pd.DataFrame,
    subgroups: pd.DataFrame,
    activity_subgroups: pd.DataFrame,
) -> CanonicalDemandResult:
    """Build unique exam demands without summing activities as if they were people.

    A subgroup owns a single participant count. Several source activities may point
    at that subgroup, which prevents duplicate counting when one exam is represented
    by several Ladok activities. Every included activity must map exactly once.
    """
    scope = build_scope_report(activities, decisions)
    _require_columns(
        demand_definitions,
        ("exam_demand_id", "plan_area", "duration_minutes", "physical_requirement"),
        "examensbehov",
    )
    _require_columns(
        subgroups,
        ("subgroup_id", "exam_demand_id", "participant_count", "count_basis"),
        "delgrupper",
    )
    _require_columns(activity_subgroups, ("activity_id", "subgroup_id"), "aktivitetsrelationer")
    demand_ids = _unique_ids(demand_definitions["exam_demand_id"], "examensbehov")
    subgroup_ids = _unique_ids(subgroups["subgroup_id"], "delgrupper")
    if set(subgroups["exam_demand_id"].astype(str)) - demand_ids:
        raise ValueError("En delgrupp refererar till ett okänt exam_demand_id.")
    counts = pd.to_numeric(subgroups["participant_count"], errors="coerce")
    if counts.isna().any() or (counts <= 0).any() or (counts % 1 != 0).any():
        raise ValueError("participant_count måste vara ett positivt heltal per delgrupp.")
    mapped_activity_ids = _unique_ids(activity_subgroups["activity_id"], "aktivitetsrelationer")
    source_ids = _unique_ids(activities["activity_id"], "Ladokaktiviteter")
    if mapped_activity_ids - source_ids:
        raise ValueError("Aktivitetsrelationer innehåller ett okänt activity_id.")
    if set(activity_subgroups["subgroup_id"].astype(str)) - subgroup_ids:
        raise ValueError("Aktivitetsrelationer innehåller ett okänt subgroup_id.")
    included_ids = set(scope.activities.loc[scope.activities["scope_status"].eq("included"), "activity_id"].astype(str))
    if mapped_activity_ids != included_ids:
        raise ValueError("Varje och endast inkluderad aktivitet måste kopplas till exakt en delgrupp.")
    mapped_subgroups = set(activity_subgroups["subgroup_id"].astype(str))
    if mapped_subgroups != subgroup_ids:
        raise ValueError("Varje delgrupp måste ha minst en källaktivitet.")
    subgroup_frame = subgroups.copy()
    subgroup_frame["participant_count"] = counts.astype(int)
    subgroup_frame["source_activity_count"] = subgroup_frame["subgroup_id"].map(
        activity_subgroups["subgroup_id"].value_counts()
    ).astype(int)
    demand_totals = subgroup_frame.groupby("exam_demand_id", as_index=False)["participant_count"].sum()
    demands = demand_definitions.merge(demand_totals, on="exam_demand_id", how="left", validate="one_to_one")
    demands["participant_count"] = demands["participant_count"].fillna(0).astype(int)
    if (demands["participant_count"] <= 0).any():
        raise ValueError("Varje exam_demand måste ha minst en definierad delgrupp.")
    metrics = {
        **scope.metrics,
        "canonical_exam_demand_count": len(demands),
        "canonical_subgroup_count": len(subgroup_frame),
        "included_participant_count": int(demands["participant_count"].sum()),
    }
    return CanonicalDemandResult(
        demands.sort_values("exam_demand_id").reset_index(drop=True),
        subgroup_frame.sort_values("subgroup_id").reset_index(drop=True),
        scope.activities,
        metrics,
    )


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], name: str) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{name} saknar kolumner: " + ", ".join(sorted(missing)))


def _unique_ids(values: pd.Series, name: str) -> set[str]:
    if values.isna().any() or values.astype(str).str.strip().eq("").any():
        raise ValueError(f"{name} innehåller tomma identifierare.")
    rendered = values.astype(str)
    duplicates = rendered[rendered.duplicated()]
    if not duplicates.empty:
        raise ValueError(f"{name} innehåller duplicerade identifierare: {duplicates.iloc[0]}.")
    return set(rendered)
