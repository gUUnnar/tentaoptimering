"""Observation of a joint run must never change it.

- The sink gives parallel threads one stable event order, in memory and in the file, and swallows its own errors.
- The solver gives identical results with and without a sink, also when recording fails.
- The events tell what happened: phases, day checks, solutions, bounds, warm start, resources and the end.
- A run saved with a sink has the same artifacts as without, plus `joint_events.jsonl`.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_joint_optimization_effects as fx  # noqa: E402
from test_joint_strategy import _dense_case, _two_day_problem  # noqa: E402
from test_joint_validation_run import CATALOG, _write_pair_dataset  # noqa: E402
from tentaoptimering.joint_contract import SolverSettings  # noqa: E402
from tentaoptimering.joint_inputs import run_real_subset  # noqa: E402
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_progress import (  # noqa: E402
    EVENT_TYPES, EVENTS_FILE, PHASES, ProgressSink, emit, phase, read_events,
)
from tentaoptimering.joint_strategy.resources import CancelToken, ExecutionBudget  # noqa: E402
from tentaoptimering.joint_strategy.warm_start import StartReport  # noqa: E402


def _signature(result) -> str:
    """What a run decides, in a stable text form (wall time and the raw status text are measurements)."""
    return json.dumps({"s": result.schedule, "a": result.assignments, "r": result.room_sessions, "c": result.costs,
                       "p": result.staff_pool_size, "o": result.solver.outcome, "b": result.solver.best_objective_bound_ore,
                       "changed": result.changed_exam_demands}, sort_keys=True, default=lambda value: value.__dict__)


def _single(strategy: str):
    """The hand case with one solver worker: the two equal small rooms make the placement a tie that a
    multi-threaded search may break differently from run to run; with one worker the whole result is fixed."""
    return replace(_two_day_problem(strategy), solver=SolverSettings(20, 1, 1, False, strategy, 0.0))


def _types(events: list[dict]) -> list[str]:
    return [event["type"] for event in events]


class SinkTests(unittest.TestCase):
    def test_threads_get_one_stable_order_in_memory_and_in_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / EVENTS_FILE
            sink = ProgressSink(path)
            threads = [threading.Thread(target=lambda n=n: [sink.emit("day", worker=n, i=i) for i in range(200)]) for n in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            sink.close()
            events = sink.events()
            self.assertEqual([event["seq"] for event in events], list(range(1, 1601)))
            self.assertEqual(sink.last_seq, 1600)
            self.assertEqual(read_events(path), events)  # the file has the same events in the same order
            self.assertTrue(all(left["t"] <= right["t"] for left, right in zip(events, events[1:])))
            for worker in range(8):  # each thread's own events stay in its own order
                self.assertEqual([e["i"] for e in events if e["worker"] == worker], list(range(200)))

    def test_held_back_events_are_recorded_last_and_in_order(self) -> None:
        sink = ProgressSink()
        sink.defer("finished")
        sink.emit("finished", outcome="optimal")
        sink.emit("phase", name="finalize", state="started")
        self.assertTrue(sink.has("finished"))  # held back counts as recorded, so nothing is reported twice
        self.assertEqual(_types(sink.events()), ["phase"])
        sink.emit("phase", name="finalize", state="finished")
        sink.release()
        self.assertEqual(_types(sink.events()), ["phase", "phase", "finished"])
        self.assertEqual([event["seq"] for event in sink.events()], [1, 2, 3])
        sink.emit("finished", outcome="again")  # no longer held back
        self.assertEqual(sink.last_seq, 4)

    def test_events_after_a_sequence_number_are_copies(self) -> None:
        sink = ProgressSink()
        for index in range(5):
            sink.emit("bound", lower_ore=index, round=1)
        self.assertEqual([event["seq"] for event in sink.events(after=3)], [4, 5])
        self.assertEqual(sink.events(after=5), [])
        sink.events()[0]["lower_ore"] = 99
        self.assertEqual(sink.events()[0]["lower_ore"], 0)

    def test_a_file_attached_late_gets_the_earlier_events_first_and_every_line_is_flushed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            sink = ProgressSink()
            sink.emit("phase", name="relaxation", state="started")
            path = Path(temp) / EVENTS_FILE
            sink.attach(path)
            sink.emit("phase", name="relaxation", state="finished")
            lines = path.read_text(encoding="utf-8").splitlines()  # read while the file is still open: flushed per line
            self.assertEqual([json.loads(line)["seq"] for line in lines], [1, 2])
            sink.close()

    def test_recording_failures_never_reach_the_caller(self) -> None:
        sink = ProgressSink()
        with self.assertLogs(level="WARNING"), mock.patch.object(ProgressSink, "_write", side_effect=RuntimeError("disk")):
            sink.emit("bound", lower_ore=1, round=1)  # does not raise
        self.assertEqual(sink.last_seq, 1)
        with tempfile.TemporaryDirectory() as temp, self.assertLogs(level="WARNING"):
            broken = ProgressSink(Path(temp))  # a directory cannot be opened as a file
            broken.emit("bound", lower_ore=1, round=1)
            self.assertEqual(broken.last_seq, 1)
        with self.assertLogs(level="WARNING"), mock.patch.object(ProgressSink, "emit", side_effect=RuntimeError("sink")):
            emit(ProgressSink(), "bound", lower_ore=1, round=1)  # even a sink that raises is held back
            with phase(ProgressSink(), "relaxation"):
                pass

    def test_no_sink_costs_nothing_and_unserialisable_values_do_not_break_the_file(self) -> None:
        emit(None, "bound", lower_ore=1, round=1)
        with phase(None, "relaxation"):
            pass
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / EVENTS_FILE
            sink = ProgressSink(path)
            sink.emit("day", value=object())
            sink.emit("day", value=1)
            sink.close()
            self.assertEqual(len(read_events(path)), 2)

    def test_a_log_cut_off_in_the_middle_of_a_line_is_still_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / EVENTS_FILE
            path.write_text('{"seq": 1, "t": 0.1, "type": "phase"}\n{"seq": 2, "t": 0.2, "ty', encoding="utf-8")
            self.assertEqual([event["seq"] for event in read_events(path)], [1])


class SolverObservationTests(unittest.TestCase):
    def test_the_hand_case_gives_identical_results_with_and_without_a_sink(self) -> None:
        for strategy in ("decomposed", "monolithic"):
            with self.subTest(strategy=strategy):
                plain = solve_joint_optimization(_single(strategy))
                sink = ProgressSink()
                observed = solve_joint_optimization(_single(strategy), progress=sink)
                self.assertEqual(_signature(observed), _signature(plain))
                self.assertEqual(observed.costs.comparable_total_cost_ore, 1300)
                finished = sink.events()[-1]
                self.assertEqual((finished["type"], finished["outcome"], finished["cost_ore"], finished["cancelled"]),
                                 ("finished", "optimal", 1300, False))

    def test_a_failing_sink_changes_nothing(self) -> None:
        plain = solve_joint_optimization(_single("decomposed"))
        with self.assertLogs(level="WARNING"), mock.patch.object(ProgressSink, "emit", side_effect=RuntimeError("sink is broken")):
            observed = solve_joint_optimization(_single("decomposed"), progress=ProgressSink())
        self.assertEqual(_signature(observed), _signature(plain))

    def test_the_events_tell_the_story_of_a_decomposed_run(self) -> None:
        sink = ProgressSink()
        result = solve_joint_optimization(_two_day_problem("decomposed"), budget=ExecutionBudget(4), progress=sink)
        events = sink.events()
        kinds = _types(events)
        self.assertEqual([event["seq"] for event in events], list(range(1, len(events) + 1)))
        for kind in ("resources", "phase", "batch", "day", "incumbent", "bound", "finished"):
            self.assertIn(kind, kinds)
        self.assertEqual(kinds.count("finished"), 1)
        self.assertEqual(kinds[-1], "finished")
        for event in events:
            self.assertIn(event["type"], EVENT_TYPES)
            self.assertTrue(set(EVENT_TYPES[event["type"]]) <= set(event), event)
        resources = next(event for event in events if event["type"] == "resources")
        self.assertEqual((resources["threads"], resources["parallel_checks"], resources["workers_per_check"]), (4, 4, 1))
        names = {event["name"] for event in events if event["type"] == "phase"}
        self.assertTrue({"relaxation", "day_checks"} <= names <= set(PHASES))
        for name in names:  # every phase that starts also finishes, in that order
            states = [event["state"] for event in events if event["type"] == "phase" and event["name"] == name]
            self.assertEqual(states, ["started", "finished"] * (len(states) // 2))
        incumbents = [event for event in events if event["type"] == "incumbent"]
        self.assertEqual(incumbents[-1]["cost_ore"], result.costs.comparable_total_cost_ore)
        self.assertTrue(all(left["cost_ore"] >= right["cost_ore"] for left, right in zip(incumbents, incumbents[1:])))
        bounds = [event["lower_ore"] for event in events if event["type"] == "bound"]
        self.assertEqual(bounds, sorted(bounds))
        self.assertLessEqual(bounds[-1], result.costs.comparable_total_cost_ore)
        days = [event for event in events if event["type"] == "day"]
        self.assertTrue(all(event["status"] in {"optimal", "feasible", "infeasible", "unknown"} for event in days))
        self.assertTrue(all(event["date"].startswith("2026-01-1") for event in days))

    def test_batches_count_up_and_end_with_every_check_done(self) -> None:
        events, rooms, overrides = _dense_case(12)
        with tempfile.TemporaryDirectory() as temp:
            problem, _ = fx._solve(Path(temp), events, rooms, overrides)
        problem = replace(problem, solver=SolverSettings(60, 5, 2, False, "decomposed", 0.0))
        plain = solve_joint_optimization(problem, budget=ExecutionBudget(4))
        sink = ProgressSink()
        observed = solve_joint_optimization(problem, budget=ExecutionBudget(4), progress=sink)
        self.assertEqual(observed.solver.outcome, plain.solver.outcome)
        if plain.solver.outcome == "optimal":  # a proven optimum has one cost, whichever of its placements is found
            self.assertEqual(observed.costs, plain.costs)
        batches = [event for event in sink.events() if event["type"] == "batch"]
        self.assertTrue(batches)
        self.assertEqual([event["seq"] for event in batches], sorted(event["seq"] for event in batches))
        last_done: dict[tuple, int] = {}
        for event in batches:
            self.assertLessEqual(event["done"], event["total"])
            self.assertLessEqual(sum(event["statuses"].values()), event["total"])
            self.assertLessEqual(event["parallel"] * event["workers_per_check"], 4)
            identity = (event["kind"], event["total"])
            if event["done"] > 0:  # a new batch of the same size starts again at 0; inside one it only grows
                self.assertGreaterEqual(event["done"], last_done.get(identity, 0))
            last_done[identity] = event["done"]
        complete = [event for event in batches if event["done"] == event["total"]]
        self.assertTrue(complete)
        self.assertTrue(all(sum(event["statuses"].values()) == event["total"] for event in complete))

    def test_a_warm_start_is_reported_with_its_source(self) -> None:
        first = solve_joint_optimization(_single("decomposed"))
        saved = {"schedule": list(first.schedule), "room_sessions": list(first.room_sessions)}
        report, sink = StartReport(source_run_id="earlier-run"), ProgressSink()
        plain = solve_joint_optimization(_single("decomposed"), saved)
        observed = solve_joint_optimization(_single("decomposed"), saved, report=report, progress=sink)
        self.assertEqual(_signature(observed), _signature(plain))
        warm = [event for event in sink.events() if event["type"] == "warm_start"]
        self.assertEqual([(event["decision"], event["source_run_id"]) for event in warm], [("accepted", "earlier-run")])
        self.assertTrue(warm[0]["explanation"])
        self.assertNotIn("source_run_id", report.to_dict())  # the saved report is unchanged
        incumbent = next(event for event in sink.events() if event["type"] == "incumbent")
        self.assertEqual(incumbent["source"], "warm start")
        self.assertIn("warm_start_check", {event["name"] for event in sink.events() if event["type"] == "phase"})

    def test_a_placement_the_instance_no_longer_allows_is_reported_as_rejected(self) -> None:
        saved = {"schedule": [{"exam_demand_id": "a", "slot_id": "gone"}], "room_sessions": [{"room_id": "big"}]}
        sink = ProgressSink()
        solve_joint_optimization(_two_day_problem("decomposed"), saved, report=StartReport(), progress=sink)
        warm = [event for event in sink.events() if event["type"] == "warm_start"]
        self.assertEqual([event["decision"] for event in warm], ["rejected"])
        self.assertIn("ledtråd", warm[0]["explanation"])

    def test_a_cancelled_run_says_so(self) -> None:
        token, sink = CancelToken(), ProgressSink()
        token.cancel()
        result = solve_joint_optimization(_two_day_problem("decomposed"), cancel=token, progress=sink)
        self.assertFalse(result.schedule)
        finished = sink.events()[-1]
        self.assertEqual((finished["type"], finished["cancelled"], finished["cost_ore"]), ("finished", True, None))


class RunArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.scenario = _write_pair_dataset(self.dir)
        self.runs = self.dir / "runs"

    def test_a_run_with_a_sink_has_the_same_artifacts_plus_the_event_log(self) -> None:
        plain = run_real_subset(self.scenario, self.dir, CATALOG, self.runs, warm_start="none")
        time.sleep(1.05)  # run ids carry the time in seconds
        sink = ProgressSink()
        observed = run_real_subset(self.scenario, self.dir, CATALOG, self.runs, warm_start="none", progress=sink)
        sink.close()
        self.assertEqual(set(observed["artifacts"]) - set(plain["artifacts"]), {EVENTS_FILE})
        self.assertEqual(set(plain["artifacts"]) - set(observed["artifacts"]), set())
        self.assertEqual(observed["result"]["costs"], plain["result"]["costs"])
        self.assertEqual(observed["result"]["schedule"], plain["result"]["schedule"])
        self.assertEqual(observed["validation"]["technical_validation"], plain["validation"]["technical_validation"])
        self.assertEqual(sink.run_id, observed["run_id"])
        saved = read_events(self.runs / observed["run_id"] / EVENTS_FILE)
        self.assertEqual(saved, sink.events())
        kinds = _types(saved)
        for kind in ("warm_start", "resources", "phase", "incumbent", "bound", "finished"):
            self.assertIn(kind, kinds)
        self.assertEqual(next(e for e in saved if e["type"] == "warm_start")["decision"], "not_used")
        self.assertEqual(kinds[-1], "finished")  # the last event: the artifacts are saved and validated before it
        self.assertEqual(kinds.count("finished"), 1)
        finalize = [(e["name"], e["state"]) for e in saved[:-1] if e["type"] == "phase" and e["name"] == "finalize"]
        self.assertEqual(finalize, [("finalize", "started"), ("finalize", "finished")])

    def test_the_run_directory_exists_while_the_solver_runs(self) -> None:
        seen: list[bool] = []
        real = solve_joint_optimization

        def spying(problem, *args, **kwargs):
            seen.append(any((path / EVENTS_FILE).is_file() for path in self.runs.iterdir()))
            return real(problem, *args, **kwargs)

        with mock.patch("tentaoptimering.joint_inputs.solve_joint_optimization", spying):
            run_real_subset(self.scenario, self.dir, CATALOG, self.runs, warm_start="none", progress=ProgressSink())
        self.assertEqual(seen, [True])

    def test_a_second_run_reports_its_warm_start_source(self) -> None:
        first = run_real_subset(self.scenario, self.dir, CATALOG, self.runs, warm_start="none")
        time.sleep(1.05)
        sink = ProgressSink()
        second = run_real_subset(self.scenario, self.dir, CATALOG, self.runs, progress=sink)
        warm = [event for event in sink.events() if event["type"] == "warm_start"]
        self.assertEqual([(event["decision"], event["source_run_id"]) for event in warm], [("accepted", first["run_id"])])
        self.assertEqual(second["warm_start"]["recheck"].keys(), StartReport().to_dict().keys())


if __name__ == "__main__":
    unittest.main()
