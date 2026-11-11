"""The repair suggestion: the smallest set of allowed changes after which the solver finds a solution.

The search is driven with a scripted `evaluate` (what a candidate set of parameter values would give), so every case is worked by
hand: which moves are taken, that no move can be dropped, that only a solution counts as possible and that nothing outside
the calendar, the dates and the fixed bookings is ever proposed.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tentaoptimering import joint_repair  # noqa: E402
from tentaoptimering.joint_api import JointRunRequest  # noqa: E402
from tentaoptimering.joint_repair import FOUND, INCOMPLETE, NOT_FOUND, NOTHING_NEEDED, SOLUTION, UNDECIDED, UNPROVEN, INFEASIBLE  # noqa: E402
from tentaoptimering.joint_strategy.resources import CancelToken  # noqa: E402

ALLOWED_PREFIXES = ("calendar.", "window.", "wish.candidate_policy", "reservations.")


def _values(**changes):
    base = {"calendar.weekdays": [1, 2, 3, 4, 5], "calendar.start_times": ["08:00", "14:00"], "calendar.start_date": "", "calendar.end_date": "",
            "window.earlier_days": 0, "window.later_days": 0, "wish.candidate_policy": "window", "reservations.policy": "block_identified"}
    return {**base, **changes}


def _problem(values, blocked_days=(), blocked_starts=(), groups=()):
    demands = [SimpleNamespace(candidate_slot_ids=(), original_date=date(2026, 1, 12) + date.resolution * (day - 1), original_start_minute=480,
                               wish_dates=(), original_slot_id=None, exam_demand_id=f"d{day}", course_code=None) for day in blocked_days]
    demands += [SimpleNamespace(candidate_slot_ids=(), original_date=date(2026, 1, 12), original_start_minute=minutes, wish_dates=(),
                                original_slot_id=None, exam_demand_id=f"s{minutes}", course_code=None) for minutes in blocked_starts]
    reservations = {"status": "read", "groups": [{"group": key, "bookings": count, "action": action, "action_parameter": key, "booked_places": 0, "rooms": []}
                                                 for key, count, action in groups]}
    return SimpleNamespace(demands=demands, parameters=[SimpleNamespace(parameter_id=key, value=value) for key, value in values.items()],
                           resource_basis={"reservations": reservations})


class Scenario:
    """A scripted world: which parameter values leave exams without an occasion, and what the solver says for a set of values."""

    def __init__(self, needs=(), solver=None, groups=(), values=None) -> None:
        self.needs, self.solver, self.groups, self.values = list(needs), solver or (lambda extra: SOLUTION), list(groups), values or _values()
        self.calls: list[tuple[dict, bool]] = []

    def blocked(self, extra) -> int:
        return sum(1 for need in self.needs if not need(extra))

    def evaluate(self, search, extra, label, solve=False, seconds=joint_repair.PROBE_SECONDS):
        self.calls.append((dict(extra), solve))
        blocked = self.blocked(extra)
        merged = {**self.values, **extra}
        days = [d for d in range(1, 8) if d not in merged["calendar.weekdays"]]
        problem = _problem(merged, blocked_days=[d for d in days if self.blocked_by_day(extra, d)], groups=self.groups)
        # the exams that are still blocked decide which moves are offered (their weekdays and start times)
        problem.demands = [item for item in problem.demands][:blocked] + [SimpleNamespace(candidate_slot_ids=("x",), original_slot_id="x", original_date=None,
                                                                                         original_start_minute=None, wish_dates=(), exam_demand_id="ok", course_code=None)]
        result = joint_repair._Evaluation(blocked, 0, problem)
        if solve and not blocked:
            result.outcome, result.seconds = self.solver(extra), 1.0
        search.attempts.append({"label": label})
        return result

    def blocked_by_day(self, extra, day) -> bool:
        return day in getattr(self, "blocked_days", ())

    def run(self):
        request = JointRunRequest(scenario="case")
        with mock.patch.object(joint_repair, "run_config", return_value=(Path("x"), None)), \
                mock.patch.object(joint_repair, "read_scenario", return_value={"scenario": {"id": "case"}, "parameters": {}}), \
                mock.patch.object(joint_repair._Search, "evaluate", lambda search, extra, label, solve=False, seconds=joint_repair.PROBE_SECONDS: self.evaluate(search, extra, label, solve, seconds)):
            return joint_repair.suggest_fix(SimpleNamespace(), request, None, CancelToken(), catalog_path=Path("catalog"))


def _needs_weekday(day):
    return lambda extra: day in extra.get("calendar.weekdays", [1, 2, 3, 4, 5])


def _needs_start(clock):
    return lambda extra: clock in extra.get("calendar.start_times", ["08:00", "14:00"])


class RepairTests(unittest.TestCase):
    def test_nothing_is_proposed_when_the_run_is_already_possible(self) -> None:
        result = Scenario().run()
        self.assertEqual((result["status"], result["parameters"], result["steps"]), (NOTHING_NEEDED, {}, []))

    def test_exams_without_an_occasion_get_exactly_the_missing_weekday(self) -> None:
        world = Scenario(needs=[_needs_weekday(6)])
        world.blocked_days = (6,)
        result = world.run()
        self.assertEqual(result["status"], FOUND)
        self.assertEqual(result["parameters"], {"calendar.weekdays": [1, 2, 3, 4, 5, 6]})  # Saturday and nothing else
        self.assertEqual([step["id"] for step in result["steps"]], ["weekday:6"])
        self.assertEqual(result["exams_without_occasion"], {"before": 1, "after": 0})
        self.assertFalse(result["explorative"])

    def test_a_move_that_the_set_does_not_need_is_dropped(self) -> None:
        # Saturday frees one exam, the wish policy frees both; the policy alone is enough, so Saturday must not be in the answer
        policy = lambda extra: extra.get("wish.candidate_policy") == "wishes_and_window"  # noqa: E731
        saturday = _needs_weekday(6)
        world = Scenario(needs=[lambda extra: policy(extra) or saturday(extra), policy], values=_values(**{"wish.candidate_policy": "wishes"}))
        world.blocked_days = (6,)
        result = world.run()
        self.assertEqual(result["status"], FOUND)
        self.assertEqual([step["id"] for step in result["steps"]], ["policy"])
        self.assertEqual(result["parameters"], {"wish.candidate_policy": "wishes_and_window"})

    def test_the_smallest_fixed_booking_group_that_is_enough_is_taken_alone(self) -> None:
        groups = [("reservations.action_no_count", 5, "keep_fixed"), ("reservations.action_not_in_ladok", 40, "keep_fixed")]
        solver = lambda extra: SOLUTION if extra.get("reservations.action_not_in_ladok") == "remove" else INFEASIBLE  # noqa: E731
        result = Scenario(groups=groups, solver=solver).run()
        self.assertEqual(result["status"], FOUND)
        self.assertEqual(result["parameters"], {"reservations.action_not_in_ladok": "remove"})  # the 5-booking group was tried first and was not enough
        self.assertTrue(result["explorative"])
        self.assertIn("explorativt", result["steps"][0]["side_effect"])
        self.assertEqual(result["verified"]["outcome"], SOLUTION)

    def test_two_groups_are_proposed_together_only_when_each_alone_is_not_enough_and_neither_can_be_dropped(self) -> None:
        groups = [("reservations.action_no_count", 5, "keep_fixed"), ("reservations.action_not_in_ladok", 40, "keep_fixed")]
        both = lambda extra: extra.get("reservations.action_no_count") == "remove" and extra.get("reservations.action_not_in_ladok") == "remove"  # noqa: E731
        result = Scenario(groups=groups, solver=lambda extra: SOLUTION if both(extra) else INFEASIBLE).run()
        self.assertEqual(result["status"], FOUND)
        self.assertEqual(result["parameters"], {"reservations.action_no_count": "remove", "reservations.action_not_in_ladok": "remove"})

    def test_an_undecided_probe_is_never_reported_as_possible(self) -> None:
        groups = [("reservations.action_not_in_ladok", 40, "keep_fixed")]
        result = Scenario(groups=groups, solver=lambda extra: UNDECIDED).run()
        self.assertEqual(result["status"], UNPROVEN)
        self.assertIsNone(result["verified"])  # no solution was found, so nothing is verified
        self.assertEqual(result["parameters"], {"reservations.action_not_in_ladok": "remove"})  # offered, but as an untested candidate
        self.assertIn("oprövat", result["summary"])

    def test_when_the_allowed_changes_cannot_help_it_says_so_and_proposes_nothing_false(self) -> None:
        groups = [("reservations.action_not_in_ladok", 40, "keep_fixed")]
        result = Scenario(groups=groups, solver=lambda extra: INFEASIBLE).run()
        self.assertIn(result["status"], (NOT_FOUND, INCOMPLETE))
        self.assertIsNone(result["verified"])
        self.assertIn("kapacitet", result["summary"])

    def test_every_proposed_parameter_belongs_to_the_allowed_kinds_of_change(self) -> None:
        worlds = []
        world = Scenario(needs=[_needs_weekday(6), _needs_start("09:00")])
        world.blocked_days = (6,)
        worlds.append(world)
        worlds.append(Scenario(groups=[("reservations.action_no_count", 5, "keep_fixed")], solver=lambda extra: SOLUTION if extra else INFEASIBLE))
        for world in worlds:
            for key in world.run()["parameters"]:
                self.assertTrue(key.startswith(ALLOWED_PREFIXES), key)  # never rooms, splitting, demand or the planning share


class ApplyTests(unittest.TestCase):
    def test_moves_add_to_the_calendar_instead_of_replacing_it(self) -> None:
        values = _values()
        moves = [joint_repair.Move("weekday:6", "weekday", "x", 6), joint_repair.Move("weekday:7", "weekday", "x", 7),
                 joint_repair.Move("start_time:09:00", "start_time", "x", "09:00"), joint_repair.Move("window:later:2", "window", "x", ("later", 2)),
                 joint_repair.Move("window:later:1", "window", "x", ("later", 1))]
        out = joint_repair._apply({}, moves, values)
        self.assertEqual(out["calendar.weekdays"], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(out["calendar.start_times"], ["08:00", "09:00", "14:00"])
        self.assertEqual(out["window.later_days"], 2)  # the wider window wins, whatever the order

    def test_a_calendar_date_is_only_widened_never_narrowed(self) -> None:
        values = _values(**{"calendar.start_date": "2026-01-12", "calendar.end_date": "2026-03-31"})
        out = joint_repair._apply({}, [joint_repair.Move("calendar:start", "calendar", "x", ("start", "2026-01-05")),
                                       joint_repair.Move("calendar:end", "calendar", "x", ("end", "2026-03-01"))], values)
        self.assertEqual((out["calendar.start_date"], out["calendar.end_date"]), ("2026-01-05", "2026-03-31"))


class RealSearchTests(unittest.TestCase):
    """The search on a small real problem (two exams on Monday 12 January) instead of a scripted one."""

    def _suggest(self, parameters):
        from test_joint_api import Workspace

        workspace = Workspace(self)
        return joint_repair.suggest_fix(workspace.storage, JointRunRequest(scenario="case", parameters=parameters), None, CancelToken(),
                                        scenarios_dir=workspace.scenarios)

    def test_a_possible_run_needs_no_change(self) -> None:
        self.assertEqual(self._suggest({})["status"], NOTHING_NEEDED)

    def test_exams_on_a_monday_with_only_wednesday_allowed_need_exactly_monday(self) -> None:
        result = self._suggest({"calendar.weekdays": [3]})
        self.assertEqual(result["status"], FOUND)
        self.assertEqual(result["parameters"], {"calendar.weekdays": [1, 3]})
        self.assertEqual(result["exams_without_occasion"], {"before": 2, "after": 0})
        self.assertEqual(result["verified"]["outcome"], SOLUTION)  # the solver really found a placement with the proposal


if __name__ == "__main__":
    unittest.main()
