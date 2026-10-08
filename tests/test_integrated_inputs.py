from pathlib import Path
import tempfile
import unittest

import pandas as pd

from tentaoptimering.integrated_config import load_integrated_term_scenario
from tentaoptimering.integrated_inputs import load_term_model_inputs


REPO_ROOT = Path(__file__).resolve().parents[1]


class IntegratedInputsTests(unittest.TestCase):
    def test_adapter_keeps_source_traceability_and_scope_completeness(self) -> None:
        scenario = load_integrated_term_scenario(
            REPO_ROOT / "config" / "scenarios" / "integrated_term_exploratory.toml"
        )
        with tempfile.TemporaryDirectory() as temporary:
            processed = Path(temporary)
            pd.DataFrame([{
                "demand_id": "demand-1", "activity_id": "activity-1", "exam_event_id": "event-1",
                "course_code": "COURSE", "scheduled_time": "08:00-10:00", "demand_value": 12,
                "demand_measure_source_field": "registered_count",
                "demand_input_status": "ready_provisional_ladok_demand", "observed_cities": "Uppsala",
            }]).to_csv(processed / "optimization_demands.csv", index=False, encoding="utf-8-sig")
            pd.DataFrame([{
                "room_id": "room-1", "capacity_seats": 20, "reference_city": "Uppsala",
                "eligible_for_exploratory_capacity_poc": True,
            }]).to_csv(processed / "optimization_rooms.csv", index=False, encoding="utf-8-sig")
            pd.DataFrame([
                {"activity_id": "activity-1", "scope_status": "included"},
                {"activity_id": "activity-2", "scope_status": "unresolved"},
            ]).to_csv(processed / "demand_scope.csv", index=False, encoding="utf-8-sig")

            result = load_term_model_inputs(processed, scenario)

        self.assertEqual(result.scope_metrics["source_activities_total"], 2)
        self.assertEqual(result.scope_metrics["unresolved_source_activities"], 1)
        self.assertEqual(result.demands[0].participants, 12)
        self.assertEqual(result.demand_traceability[0]["source_activity_id"], "activity-1")


if __name__ == "__main__":
    unittest.main()
