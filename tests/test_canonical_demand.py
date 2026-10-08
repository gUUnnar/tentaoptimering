from __future__ import annotations

import unittest

import pandas as pd

from tentaoptimering.canonical_demand import (
    build_canonical_exam_demands,
    build_scope_report,
    provisional_scope_decisions,
    unresolved_scope_decisions,
)


class CanonicalDemandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.activities = pd.DataFrame({"activity_id": ["a1", "a2", "a3"]})

    def test_initial_scope_report_keeps_every_activity_visible(self) -> None:
        report = build_scope_report(self.activities, unresolved_scope_decisions(self.activities))
        self.assertEqual(report.metrics["source_activity_count"], 3)
        self.assertEqual(report.metrics["unresolved_activity_count"], 3)
        self.assertFalse(report.metrics["scope_complete_for_whole_population"])

    def test_provisional_scope_keeps_technical_gaps_unresolved(self) -> None:
        candidates = pd.DataFrame(
            {
                "activity_id": ["a1", "a2", "a3"],
                "relationship_status": ["unambiguous_candidate", "ambiguous_candidates", "unambiguous_candidate"],
                "demand_input_status": ["ready_provisional_ladok_demand", "not_selected_for_optimization", "missing_configured_demand_value"],
            }
        )
        report = build_scope_report(self.activities, provisional_scope_decisions(self.activities, candidates))
        self.assertEqual(report.metrics["included_activity_count"], 1)
        self.assertEqual(report.metrics["unresolved_activity_count"], 2)
        self.assertFalse(report.metrics["scope_complete_for_whole_population"])

    def test_multiple_activities_can_form_one_exam_without_double_counting(self) -> None:
        decisions = pd.DataFrame(
            {
                "activity_id": ["a1", "a2", "a3"],
                "scope_status": ["included", "included", "excluded"],
                "scope_reason_code": ["physical_exam", "physical_exam", "digital_only"],
                "evidence_reference": ["rule-1", "rule-1", "rule-2"],
            }
        )
        result = build_canonical_exam_demands(
            self.activities,
            decisions,
            pd.DataFrame({"exam_demand_id": ["e1"], "plan_area": ["Uppsala"], "duration_minutes": [120], "physical_requirement": ["physical"]}),
            pd.DataFrame({"subgroup_id": ["g1"], "exam_demand_id": ["e1"], "participant_count": [40], "count_basis": ["verified_group"]}),
            pd.DataFrame({"activity_id": ["a1", "a2"], "subgroup_id": ["g1", "g1"]}),
        )
        self.assertEqual(result.exam_demands.iloc[0]["participant_count"], 40)
        self.assertEqual(result.demand_subgroups.iloc[0]["source_activity_count"], 2)
        self.assertEqual(result.metrics["excluded_activity_count"], 1)

    def test_included_activity_without_subgroup_is_rejected(self) -> None:
        decisions = unresolved_scope_decisions(self.activities)
        decisions.loc[0, "scope_status"] = "included"
        with self.assertRaisesRegex(ValueError, "inkluderad aktivitet"):
            build_canonical_exam_demands(
                self.activities,
                decisions,
                pd.DataFrame(columns=["exam_demand_id", "plan_area", "duration_minutes", "physical_requirement"]),
                pd.DataFrame(columns=["subgroup_id", "exam_demand_id", "participant_count", "count_basis"]),
                pd.DataFrame(columns=["activity_id", "subgroup_id"]),
            )


if __name__ == "__main__":
    unittest.main()
