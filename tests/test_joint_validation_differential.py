"""Differential check: random small problems solved by the optimizer must pass the independent validator.

A technical `fail` here means the optimizer or the validator disagrees with the other about a rule.
The validator never calls the optimizer; only the saved artifacts are compared.
"""

from __future__ import annotations

from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_joint_optimization_effects as fx  # noqa: E402
from tentaoptimering.joint_contract import write_problem, write_result  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402
from joint_validation_cases import write_run  # noqa: E402

import json  # noqa: E402

KINDS = ("Ordinarie tenta", "Omtenta", "Dugga", "Hemtenta")
DIGITAL = ("Ja", "Nej", None, "Ja | Nej")
STATUS = ("all_places_support_e_exam", "supports_e_exam", "not_stated")
STARTS = (("08:00", "12:00"), ("08:00", "13:00"), ("14:00", "17:00"), ("14:00", "18:00"), ("09:00", "11:00"))


def _random_case(seed: int):
    rng = random.Random(seed)
    events = []
    for index in range(rng.randint(2, 6)):
        start, end = rng.choice(STARTS)
        events.append(fx._event(
            f"E{index}", day=f"2026-01-{rng.choice((12, 13, 14)):02d}", start=start, end=end, kind=rng.choice(KINDS),
            digital=rng.choice(DIGITAL), count=rng.choice((5, 20, 40, 55, 80, 120)),
        ))
    rooms = [(f"uu-r{i}", f"Adress {rng.randint(1, 2)}", rng.choice((40, 60, 100, 130)), rng.choice(STATUS)) for i in range(rng.randint(2, 4))]
    overrides = {
        "window.earlier_days": rng.randint(0, 2), "window.later_days": rng.randint(0, 2),
        "calendar.weekdays": rng.choice(([1, 2, 3, 4, 5], [1, 2, 3], [1, 3, 5])),
        "calendar.start_times": rng.choice((["08:00", "14:00"], ["08:00"], ["09:00", "13:00", "14:00"])),
        "calendar.turnaround_minutes": rng.choice((0, 15, 30)),
        "rooms.allow_split_across_buildings": rng.random() < 0.4, "rooms.max_rooms_per_exam": rng.choice((1, 2, 8)),
        "staffing.ladder": rng.choice((
            [{"max_participants": 60, "required_staff": 1}, {"max_participants": 150, "required_staff": 2}],
            [{"max_participants": 50, "required_staff": 1}, {"max_participants": 100, "required_staff": 2}, {"max_participants": 300, "required_staff": 3}],
        )),
        "staffing.preparation_minutes": rng.choice((0, 15, 30)), "staffing.closing_minutes": rng.choice((0, 15, 30)),
        "cost.room_annual_per_seat_ore": rng.choice((0, 100, 200)), "cost.staff_annual_ore": rng.choice((0, 1000, 5000)),
        "cost.staff_session_ore": rng.choice((0, 50)), "digital.partial_support_policy": rng.choice(("allow_unverified", "exclude")),
        "digital.unknown_demand_policy": rng.choice(("require_e_exam", "assume_paper")),
        "demand.variation_pct": rng.choice((0, 0, 10, -10)),
    }
    return events, rooms, overrides


class DifferentialTests(unittest.TestCase):
    SEEDS = range(40)

    def test_optimizer_results_pass_the_independent_validator(self) -> None:
        outcomes = {"optimal": 0, "feasible_not_proven": 0, "infeasible": 0}
        for seed in self.SEEDS:
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as temp:
                events, rooms, overrides = _random_case(seed)
                try:
                    problem, result = fx._solve(Path(temp), events, rooms, overrides)
                except ValueError as error:  # e.g. an exam without any candidate is reported, not raised
                    self.fail(f"seed {seed}: adaptern avvisade indata: {error}")
                outcomes[result.solver.outcome] = outcomes.get(result.solver.outcome, 0) + 1
                run = Path(temp) / "run"
                run.mkdir()
                write_problem(problem, run / "joint_input.json")
                write_result(result, run / "joint_result.json")
                problem_json = json.loads((run / "joint_input.json").read_text(encoding="utf-8"))
                result_json = json.loads((run / "joint_result.json").read_text(encoding="utf-8"))
                write_run(run, problem_json, result_json)
                payload = validate_run(run)
                failing = [(item["rule_id"], item["reason"], item["objects"][:3]) for item in payload["rules"] if item["status"] == "fail"]
                self.assertEqual(failing, [], f"seed {seed} ({result.solver.outcome})")
        self.assertGreaterEqual(outcomes["optimal"], 10, outcomes)  # the sample must exercise real solutions
        self.assertGreaterEqual(outcomes["infeasible"], 1, outcomes)  # and the no-solution path


if __name__ == "__main__":
    unittest.main()
