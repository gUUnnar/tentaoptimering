"""Random small problems with paid staff time, travel, external hire and fixed bookings, solved by both strategies.

Three independent implementations must agree: the optimiser (the solver's own cost), `joint_pricing` (used to price the actual booking and to
compare alternatives) and the independent validator. The two strategies must reach the same optimum.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from joint_validation_cases import write_run  # noqa: E402
from tentaoptimering.joint_contract import (  # noqa: E402
    INPUT_SCHEMA_VERSION, CandidateSlot, ExamDemand, JointOptimizationInput, ParticipantGroup, Reservation, Room, ScopeSummary, SolverSettings,
    StaffingCostPolicy, StaffingStep, write_problem, write_result,
)
from tentaoptimering.joint_costing import priced_sessions  # noqa: E402
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_pricing import COMPONENTS, price  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402

DAYS = (date(2026, 1, 12), date(2026, 1, 13))


def random_problem(seed: int, strategy: str) -> JointOptimizationInput:
    rng = random.Random(seed)
    slots = tuple(CandidateSlot(f"{day.day}-{start}", day, f"{start // 60:02d}:00", start, 1200) for day in DAYS for start in (480, 840))
    demands = []
    for index in range(rng.randint(2, 4)):
        count = rng.choice((20, 60, 90, 130))
        candidates = tuple(slot.slot_id for slot in slots if rng.random() < 0.7) or (slots[0].slot_id,)
        demands.append(ExamDemand(f"e{index}", (ParticipantGroup(f"g{index}", count, (f"a{index}",), "registered_count"),), rng.choice((60, 120, 180)), "Uppsala",
                                  candidates, candidates[0], original_date=slots[0].scheduled_date, original_start_minute=480, course_code=f"c{index}"))
    rooms = tuple(
        Room(f"r{index}", f"b{rng.randint(1, 2)}", "Uppsala", rng.choice((60, 100, 150)), rng.choice((0, 500, 3000, 8000)), rng.choice((0, 0, 700)),
             travel_paid_minutes=rng.choice((0, 0, 30, 90)), kind="external" if index == 0 else "internal")
        for index in range(rng.randint(2, 4))
    )
    reservations = tuple(
        Reservation(f"b{n}", rng.choice(rooms).room_id, rng.choice(DAYS), start, start + rng.choice((120, 240)))
        for n, start in enumerate(rng.sample((480, 840), rng.randint(0, 2)))
    )
    staffing = StaffingCostPolicy((StaffingStep(80, 1), StaffingStep(160, 2)), rng.choice((0, 1000)), rng.choice((0, 50)), rng.choice((0, 30)), rng.choice((0, 30)),
                                  rng.choice((5, 10, 25)), rng.choice((0, 90, 120)))
    return JointOptimizationInput(INPUT_SCHEMA_VERSION, f"random-{seed}", "hash", slots, tuple(demands), rooms, staffing, SolverSettings(60, seed, 1, False, strategy), (),
                                  ScopeSummary(len(demands), len(demands), 0, 0, len(demands), sum(item.participant_count for item in demands)), rng.choice((0, 30)),
                                  reservations=reservations)


class PaidTimeDifferentialTests(unittest.TestCase):
    SEEDS = range(30)

    def test_the_three_implementations_agree_and_the_strategies_reach_the_same_optimum(self) -> None:
        solved = infeasible = 0
        for seed in self.SEEDS:
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as temp:
                mono_problem, deco_problem = random_problem(seed, "monolithic"), random_problem(seed, "decomposed")
                mono, deco = solve_joint_optimization(mono_problem), solve_joint_optimization(deco_problem)
                if mono.solver.outcome == "infeasible":
                    infeasible += 1
                    self.assertIn(deco.solver.outcome, ("infeasible", "no_feasibility_conclusion"), f"seed {seed}")
                    continue
                solved += 1
                self.assertEqual(mono.solver.outcome, "optimal", f"seed {seed}")
                if deco.solver.outcome == "optimal":
                    self.assertEqual(deco.costs.comparable_total_cost_ore, mono.costs.comparable_total_cost_ore, f"seed {seed}")
                for name, problem, result in (("monolithic", mono_problem, mono), ("decomposed", deco_problem, deco)):
                    if not result.costs:
                        continue
                    # the pricing module reproduces every component the solver reported (the pool is the solver's own figure)
                    priced = price(problem, priced_sessions(problem, result.room_sessions))
                    reported = result.costs
                    for component in COMPONENTS:
                        if component != "annual_staff_pool_cost_ore":
                            self.assertEqual(priced[component], getattr(reported, component), f"seed {seed} {name} {component}")
                    run = Path(temp) / name
                    run.mkdir()
                    write_problem(problem, run / "joint_input.json")
                    write_result(result, run / "joint_result.json")
                    write_run(run, json.loads((run / "joint_input.json").read_text(encoding="utf-8")), json.loads((run / "joint_result.json").read_text(encoding="utf-8")))
                    failing = [(item["rule_id"], item["reason"][:200]) for item in validate_run(run)["rules"] if item["status"] == "fail"]
                    self.assertEqual(failing, [], f"seed {seed} {name}")
        self.assertGreaterEqual(solved, 10, (solved, infeasible))  # the sample must exercise real solutions


if __name__ == "__main__":
    unittest.main()
