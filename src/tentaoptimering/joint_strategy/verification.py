"""Exact verification of relaxation plans and history polish.

All checks go through `Checker`, which caches results, keeps every step inside the run's deadline,
shares one thread and memory budget between the checks and records how much time each kind of step used.
Independent checks (one per day) are run as an ordered parallel batch; checks that depend on each other
(diagnosis and repair of failed days) stay sequential.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from datetime import date
from functools import partial
import logging
import time
from typing import Iterator, NamedTuple

from ..joint_blocking import reserved_rooms
from ..joint_contract import JointOptimizationInput
from ..joint_costing import paid_cost_ore
from ..joint_progress import ProgressSink, phase
from .aggregate import Cut, Plan
from .batch_progress import BatchReporter
from .resources import CancelToken, ExecutionBudget, plan_batch, run_ordered, task_memory_mb
from .subproblems import Part, infeasible_core, restrict, solve_part

LOG = logging.getLogger(__name__)

DAY_SECONDS = 10.0      # per day check
BLOCK_SECONDS = 20.0    # per repair of failed days with their neighbours
CORE_SECONDS = 10.0     # to shrink a failed day to the exams that cause it

Parts = dict[frozenset[date], Part]
Outcome = tuple[str, Part | None, int | None]


class Request(NamedTuple):
    """One exact check of a block of days."""

    kind: str
    block: frozenset[date]
    exams: frozenset[str]
    cap: int | None
    rooms: tuple
    extra: frozenset[str] = frozenset()
    seconds: float = DAY_SECONDS
    fixed: dict[str, str] | None = None


class Checker:
    """Cached, deadline-bounded exact checks of day blocks."""

    def __init__(
        self, problem: JointOptimizationInput, deadline: float, budget: ExecutionBudget | None = None,
        cancel: CancelToken | None = None, progress: ProgressSink | None = None,
    ) -> None:
        self.problem = problem
        self.progress = progress  # observation only: the checks never read it
        self.deadline = deadline
        self.budget = (budget or ExecutionBudget()).resolve(problem.solver)
        self.cancel = cancel or CancelToken()
        self.cache: dict[tuple, Outcome] = {}
        self.seconds: dict[str, float] = defaultdict(float)       # wall time per kind of step
        self.task_seconds: dict[str, float] = defaultdict(float)  # summed time of the individual checks
        self.calls: dict[str, int] = defaultdict(int)
        self._slot_day = {slot.slot_id: slot.scheduled_date for slot in problem.slots}
        self._candidates = {item.exam_demand_id: item.candidate_slot_ids for item in problem.demands}

    @property
    def expired(self) -> bool:
        """The run's time is used up or the run was cancelled: nothing more may start."""
        return time.perf_counter() >= self.deadline or self.cancel.cancelled

    @contextmanager
    def until(self, seconds: float) -> Iterator[None]:
        """Limit the checks inside the block to `seconds` from now (never beyond the run's deadline)."""
        original = self.deadline
        self.deadline = min(original, time.perf_counter() + seconds)
        try:
            yield
        finally:
            self.deadline = original

    def check(self, kind: str, block: frozenset[date], exams: frozenset[str], cap: int | None, rooms: tuple,
              extra: frozenset[str] = frozenset(), seconds: float = DAY_SECONDS, fixed: dict[str, str] | None = None) -> Outcome:
        return self.check_many([Request(kind, block, exams, cap, rooms, extra, seconds, fixed)])[0]

    def check_many(self, requests: list[Request]) -> list[Outcome]:
        """Check independent blocks, in parallel within the thread and memory budget.

        The results come back in request order and a check gets the same worker count however the others
        finish, so the outcome does not depend on completion order. A check that stops at its time limit
        with the reduced worker count is repeated alone with all threads before it counts as failed.
        """
        keys = [_key(request) for request in requests]
        results = {key: self.cache[key] for key in keys if key in self.cache}
        pending = {key: request for key, request in zip(keys, requests) if key not in results}
        if pending:
            results.update(self._solve_batch(pending))
        return [results[key] for key in keys]

    def _solve_batch(self, pending: dict[tuple, Request]) -> dict[tuple, Outcome]:
        items = list(pending.items())
        started = time.perf_counter()
        biggest = max(self._pairs(request) for _, request in items)
        parallel, workers = plan_batch(len(items), task_memory_mb(biggest), self.budget)
        settings = self.budget.settings(self.problem.solver, workers)
        reporter = BatchReporter(self.progress, items[0][1].kind, len(items), parallel, workers)
        outcomes = run_ordered([partial(self._solve_reported, request, settings, reporter) for _, request in items], parallel, self.cancel)
        repeated = 0
        if workers < self.budget.threads:
            full = self.budget.settings(self.problem.solver)
            for index, ((result, _), (_, request)) in enumerate(zip(outcomes, items)):
                if result[0] == "unknown" and not self.expired:
                    reporter.started(request)
                    outcomes[index] = self._solve_one(request, full)
                    reporter.repeated(request, *outcomes[index])
                    repeated += 1
        reporter.finish([result[0] for result, _ in outcomes])
        fresh: dict[tuple, Outcome] = {}
        for (key, request), (result, elapsed) in zip(items, outcomes):
            self.calls[request.kind] += 1
            self.task_seconds[request.kind] += elapsed
            fresh[key] = result
            if result[0] == "unknown" and self.expired:
                continue  # a deadline miss or an interrupt is not cached: it says nothing about the block
            self.cache[key] = result
        self.seconds[items[0][1].kind] += time.perf_counter() - started
        if len(items) > 1:
            LOG.debug("batch of %d %s checks: %d in parallel x %d workers, %.1f s wall, %.1f s summed, %d repeated with all threads",
                      len(items), items[0][1].kind, parallel, workers, time.perf_counter() - started,
                      sum(elapsed for _, elapsed in outcomes), repeated)
        return fresh

    def _solve_reported(self, request: Request, settings, reporter: BatchReporter) -> tuple[Outcome, float]:
        reporter.started(request)
        outcome, elapsed = self._solve_one(request, settings)
        reporter.checked(request, outcome, elapsed)
        return outcome, elapsed

    def _solve_one(self, request: Request, settings) -> tuple[Outcome, float]:
        started = time.perf_counter()
        result = solve_part(restrict(self.problem, request.block, set(request.exams), request.rooms, request.fixed),
                            request.block, request.cap, request.extra, request.seconds, self.deadline, settings, self.cancel)
        return result, time.perf_counter() - started

    def _pairs(self, request: Request) -> int:
        """Exam x candidate slot x room triples of a check: the size that drives its memory."""
        slots = sum(
            1 if request.fixed is not None else sum(1 for slot in self._candidates[exam] if self._slot_day[slot] in request.block)
            for exam in request.exams
        )
        return slots * max(1, len(request.rooms))

    def core(self, block, exams, rooms, cap) -> frozenset[str]:
        started = time.perf_counter()
        core = infeasible_core(self.problem, block, set(exams), rooms, cap, CORE_SECONDS, self.deadline,
                               self.budget.settings(self.problem.solver), self.cancel)
        self.seconds["core"] += time.perf_counter() - started
        self.calls["core"] += 1
        return core


def _key(request: Request) -> tuple:
    return (request.block, request.exams, frozenset(room.room_id for room in request.rooms), request.cap, request.extra,
            request.fixed is not None)


def by_day(problem: JointOptimizationInput, choice: dict[str, str]) -> dict[date, frozenset[str]]:
    slots = {slot.slot_id: slot for slot in problem.slots}
    days: dict[date, set[str]] = defaultdict(set)
    for exam, slot_id in choice.items():
        days[slots[slot_id].scheduled_date].add(exam)
    return {day: frozenset(exams) for day, exams in days.items()}


def verify(checker: Checker, plan: Plan) -> tuple[Parts | None, list[Cut]]:
    """Check each day exactly; learn cuts from proven failures; repair; fall back to more staff or rooms."""
    problem = checker.problem
    days = sorted({slot.scheduled_date for slot in problem.slots})
    exams_on = by_day(problem, plan.choice)
    portfolio = tuple(room for room in problem.rooms if room.room_id in plan.owned)
    cap = plan.pool if problem.staffing.annual_cost_ore_per_staff > 0 else None
    parts: Parts = {}
    failed: list[date] = []
    ordered = sorted(exams_on)
    with phase(checker.progress, "day_checks"):
        outcomes = checker.check_many([Request("day", frozenset({day}), exams_on[day], cap, portfolio) for day in ordered])
    for day, (status, part, _) in zip(ordered, outcomes):  # the days are independent: one parallel batch, in date order
        if part is None:
            LOG.debug("day %s failed: %s (%d exams)", day, status, len(exams_on[day]))
            failed.append(day)
        else:
            parts[frozenset({day})] = part
    with phase(checker.progress if failed else None, "repair"):  # diagnosis, cuts and repair of the failed days
        cuts: list[Cut] = []
        fallback: dict[date, Part | None] = {}
        for day in list(failed):
            # Diagnose the day alone; only proven infeasibility becomes a cut, never a timeout.
            block, exams = frozenset({day}), exams_on[day]
            capped_status = checker.check("day", block, exams, cap, portfolio)[0]
            status, part, pool_bound = checker.check("diagnosis", block, exams, None, portfolio)
            if part is not None and (cap is None or peak_staff(problem, list(part.sessions)) <= cap):
                parts[block] = part  # the capped check only timed out; this placement fits the plan's pool
                failed.remove(day)
                continue
            if not checker.expired:
                if status == "infeasible":
                    cuts.append(("rooms", block, checker.core(block, exams, portfolio, None), plan.owned, 0))
                elif cap is not None:
                    if pool_bound is not None and pool_bound > cap:
                        cuts.append(("pool", block, exams, plan.owned, pool_bound))
                    if capped_status == "infeasible":
                        cuts.append(("pool", block, checker.core(block, exams, portfolio, cap), plan.owned, cap + 1))
            fallback[day] = part
        for block in _blocks(failed, days):
            # Repair with the plan's portfolio and pool: exams may move between the failed day and its neighbours.
            exams = frozenset().union(*(exams_on.get(day, frozenset()) for day in block))
            status, part, _ = checker.check("repair", block, exams, cap, portfolio, seconds=BLOCK_SECONDS)
            LOG.debug("repair %s..%s: %s", min(block), max(block), status)
            if part is not None:
                for key in [key for key in parts if key <= block]:
                    del parts[key]
                parts[block] = part
                continue
            for day in sorted(block & set(failed)):
                # Upper bound: the failed day alone with more staff, or also with rooms outside the portfolio.
                part = fallback[day]
                if part is None:
                    extra = frozenset(room.room_id for room in problem.rooms) - plan.owned
                    part = checker.check("fallback", frozenset({day}), exams_on[day], None, problem.rooms, extra)[1]
                if part is None:
                    return None, cuts
                parts[frozenset({day})] = part
        return parts, cuts


def prefer_history(checker: Checker, parts: Parts, economic: Plan, history: Plan) -> Parts:
    """Swap in the history-preferring dates wherever they verify with the same portfolio and pool.

    Exams that the two plans put on different days link those days; each linked group of days is
    taken from one plan as a whole, so every exam is still placed exactly once. A group is swapped
    only when all its days pass the exact check under the economic plan's portfolio and pool, and
    the total cost does not rise.
    """
    problem = checker.problem
    old, new = by_day(problem, economic.choice), by_day(problem, history.choice)
    old_day = {exam: day for day, exams in old.items() for exam in exams}
    new_day = {exam: day for day, exams in new.items() for exam in exams}
    groups = _linked_days([(old_day[exam], new_day[exam]) for exam in old_day if old_day[exam] != new_day[exam]])
    portfolio = tuple(room for room in problem.rooms if room.room_id in economic.owned)
    cap = economic.pool if problem.staffing.annual_cost_ore_per_staff > 0 else None
    swapped = 0
    open_groups = [group for group in groups if not any(key & group and len(key) > 1 for key in parts)]  # repaired blocks stay
    checker.check_many([Request("history", frozenset({day}), new[day], cap, portfolio)
                        for group in open_groups for day in sorted(group) if new.get(day)])  # fills the cache in parallel
    for group in groups:
        if checker.expired:
            break
        if group not in open_groups:
            continue  # a repaired multi-day block; leave it as verified
        trial = {key: part for key, part in parts.items() if not key & group}
        for day in sorted(group):
            if new.get(day):
                part = checker.check("history", frozenset({day}), new[day], cap, portfolio)[1]
                if part is None:
                    break
                trial[frozenset({day})] = part
        else:
            if cost(problem, list(trial.values()))[-1] <= cost(problem, list(parts.values()))[-1]:
                parts, swapped = trial, swapped + 1
    LOG.debug("history polish: %d of %d linked day groups swapped", swapped, len(groups))
    return parts


def _linked_days(edges: list[tuple[date, date]]) -> list[frozenset[date]]:
    parent: dict[date, date] = {}

    def find(day: date) -> date:
        parent.setdefault(day, day)
        while parent[day] != day:
            parent[day] = parent[parent[day]]
            day = parent[day]
        return day

    for left, right in edges:
        parent[find(left)] = find(right)
    groups: dict[date, set[date]] = defaultdict(set)
    for day in list(parent):
        groups[find(day)].add(day)
    return [frozenset(group) for group in groups.values()]


def _blocks(failed: list[date], days: list[date], radius: int = 1) -> list[frozenset[date]]:
    blocks: list[set[date]] = []
    for day in failed:
        index = days.index(day)
        block = set(days[max(0, index - radius): index + radius + 1])
        if blocks and blocks[-1] & block:
            blocks[-1] |= block
        else:
            blocks.append(block)
    return [frozenset(block) for block in blocks]


def peak_staff(problem: JointOptimizationInput, sessions: list[dict]) -> int:
    """Concurrent required staff at every slot start minus preparation, as in the joint model."""
    slots = {slot.slot_id: slot for slot in problem.slots}
    prep, closing = problem.staffing.preparation_minutes, problem.staffing.closing_minutes
    by_date: dict[date, list[tuple[int, int, int]]] = defaultdict(list)
    for row in sessions:
        slot = slots[row["slot_id"]]
        end = row["available_again_minute"] - problem.turnaround_minutes
        by_date[slot.scheduled_date].append((slot.start_minute - prep, end + closing, row["required_staff"]))
    peak = 0
    for checkpoint_slot in problem.slots:
        checkpoint = checkpoint_slot.start_minute - prep
        active = sum(staff for begin, end, staff in by_date.get(checkpoint_slot.scheduled_date, ()) if begin <= checkpoint < end)
        peak = max(peak, active)
    return peak


def cost(problem: JointOptimizationInput, parts: list[Part]) -> tuple[int, int, int, int, int, int, int]:
    """(pool, room cost, external, pool cost, per-session staff cost, paid staff time cost, total) of the assembled parts."""
    sessions = [row for part in parts for row in part.sessions]
    used = {row["room_id"] for row in sessions} | reserved_rooms(problem)  # a reserved room is in use through its reservation
    rooms = {room.room_id: room for room in problem.rooms}
    pool = peak_staff(problem, sessions)
    room_cost = sum(rooms[room].annual_fixed_cost_ore for room in used)
    external = sum(rooms[row["room_id"]].external_session_cost_ore for row in sessions)
    pool_cost = problem.staffing.annual_cost_ore_per_staff * pool
    session_cost = problem.staffing.cost_ore_per_staff_session * sum(row["required_staff"] for row in sessions)
    paid = paid_cost_ore(problem, sessions) if problem.staffing.paid_minute_cost_ore else 0
    return pool, room_cost, external, pool_cost, session_cost, paid, room_cost + external + pool_cost + session_cost + paid
