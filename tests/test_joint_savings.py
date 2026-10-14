from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tentaoptimering.app_storage import AppStorage
from tentaoptimering.joint_savings import SCENARIO_COPY, baseline_content, baseline_key, savings
from tentaoptimering.joint_scenarios import read_scenario

BUNDLED = Path(__file__).resolve().parents[1] / "config" / "scenarios" / "joint_underlay_period.toml"
RUN = "20261013T000000Z-joint_underlay_period_2026"


def _write_run(directory: Path, cost: int | None, bound: int | None, outcome: str = "optimal", complete: bool = True, valid: str = "pass",
               room: int = 0, staff: int = 0) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    result = {"solver": {"outcome": outcome, "objective_value_ore": cost, "best_objective_bound_ore": bound},
              "coverage": {"technical_placement_complete": complete, "exam_demands_total": 12},
              "costs": {"annual_room_cost_ore": room, "annual_staff_pool_cost_ore": staff, "external_room_session_cost_ore": 0,
                        "staff_session_cost_ore": 0, "comparable_total_cost_ore": cost} if cost is not None else None,
              "staff_pool_size": 3, "changed_exam_demands": 4}
    (directory / "joint_result.json").write_text(json.dumps(result), encoding="utf-8")
    (directory / "joint_validation.json").write_text(json.dumps({"summary": {"technical_validation": valid}}), encoding="utf-8")


class SavingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.storage = AppStorage(Path(self.temporary.name))
        self.content = read_scenario(BUNDLED)
        directory = self.storage.runs_dir / RUN
        directory.mkdir()
        (directory / SCENARIO_COPY).write_text(BUNDLED.read_text(encoding="utf-8"), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _baseline(self, **kwargs) -> None:
        _write_run(self.storage.root / "baselines" / baseline_key(self.storage, self.content) / "base-run", **kwargs)

    def test_nulage_moves_no_exam_and_leaves_the_scenario_alone(self) -> None:
        baseline = baseline_content(self.content)
        self.assertEqual(baseline["parameters"]["flex.movable_types"], [])
        self.assertNotEqual(self.content["parameters"]["flex.movable_types"], [])
        self.assertEqual({k: v for k, v in baseline["parameters"].items() if k not in ("flex.movable_types", "solver.time_limit_seconds")},
                         {k: v for k, v in self.content["parameters"].items() if k not in ("flex.movable_types", "solver.time_limit_seconds")})

    def test_the_saved_nulage_is_reused_only_for_the_same_scenario_and_underlay(self) -> None:
        key = baseline_key(self.storage, self.content)
        self.assertEqual(key, baseline_key(self.storage, read_scenario(BUNDLED)))
        other = read_scenario(BUNDLED)
        other["parameters"]["cost.room_annual_per_seat_ore"] = 1
        self.assertNotEqual(key, baseline_key(self.storage, other))
        (self.storage.processed_dir / "underlay.json").write_text(json.dumps({"prepared_id": "ny"}), encoding="utf-8")
        self.assertNotEqual(key, baseline_key(self.storage, self.content))

    def test_without_a_verified_run_there_is_no_potential(self) -> None:
        _write_run(self.storage.runs_dir / RUN, None, None, outcome="infeasible", complete=False)
        self.assertEqual(savings(self.storage, RUN)["state"], "unavailable")

    def test_a_verified_run_without_a_computed_nulage_is_missing_one(self) -> None:
        _write_run(self.storage.runs_dir / RUN, 100, 100)
        self.assertEqual(savings(self.storage, RUN)["state"], "missing")

    def test_potential_is_nulage_minus_run_with_a_range_from_the_proven_bounds(self) -> None:
        _write_run(self.storage.runs_dir / RUN, 500, 480, room=300, staff=200)
        self._baseline(cost=900, bound=850, room=600, staff=300)
        result = savings(self.storage, RUN)
        self.assertEqual((result["state"], result["potential_ore"]), ("ready", 400))
        self.assertEqual((result["potential_low_ore"], result["potential_high_ore"]), (850 - 500, 900 - 480))
        self.assertEqual([(c["label"], c["baseline_ore"], c["run_ore"]) for c in result["components"]], [("Lokaler", 600, 300), ("Vaktpool", 300, 200)])

    def test_a_nulage_without_a_verified_solution_gives_no_saving(self) -> None:
        _write_run(self.storage.runs_dir / RUN, 500, 500)
        self._baseline(cost=None, bound=None, outcome="infeasible", complete=False)
        result = savings(self.storage, RUN)
        self.assertEqual(result["state"], "unavailable")
        self.assertIn("låsta datum", result["reason"])

    def test_a_run_that_failed_validation_has_no_potential(self) -> None:
        _write_run(self.storage.runs_dir / RUN, 500, 500, valid="fail")
        self.assertEqual(savings(self.storage, RUN)["state"], "unavailable")


if __name__ == "__main__":
    unittest.main()
