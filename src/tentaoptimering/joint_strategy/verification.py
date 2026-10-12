"""Exact verification of relaxation plans, history polish and warm starts.

All checks go through `Checker`, which caches results, keeps every step inside the run's deadline
and records how much time each kind of step used.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import logging
import time

from ..joint_contract import JointOptimizationInput
from .aggregate import Cut, Plan
from .subproblems import Part, infeasible_core, restrict, solve_part

LOG = logging.getLogger(__name__)

DAY_SECONDS = 10.0      # per day check
BLOCK_SECONDS = 20.0    # per repair of failed days with their neighbours
CORE_SECONDS = 10.0     # to shrink a failed day to the exams that cause it

Parts = dict[frozenset[date], Part]


class Checker:
    """Cached, deadline-bounded exact checks of day blocks."""

    def __init__(self, problem: JointOptimizationInput, deadline: float) -> None:
        self.problem = problem
        self.deadline = deadline
        self.cache: dict[tuple, tuple[str, Part | None, int | None]] = {}
        self.seconds: dict[str, float] = defaultdict(float)
        self.calls: dict[str, int] = defaultdict(int)

    def check(self, kind: str, block: frozenset[date], exams: frozenset[str], cap: int | None, rooms: tuple,
              extra: frozenset[str] = frozenset(), seconds: float = DAY_SECONDS, fixed: dict[str, str] | None = None):
        key = (block, exams, frozenset(room.room_id for room in rooms), cap, extra, fixed is not None)
        if key not in self.cache:
            started = time.perf_counter()
            result = solve_part(restrict(self.problem, block, set(exams), rooms, fixed), block, cap, extra,
                                seconds, self.deadline, self.problem.solver)
            self.seconds[kind] += time.perf_counter() - started
            self.calls[kind] += 1
            if result[0] == "unknown" and time.perf_counter() >= self.deadline:
                return result  # a deadline miss is not cached: it says nothing about the block
            self.cache[key] = result
        return self.cache[key]

    def core(self, block, exams, rooms, cap) -> frozenset[str]:
        started = time.perf_counter()
        core = infeasible_core(self.problem, block, set(exams), rooms, cap, CORE_SECONDS, self.deadline, self.problem.solver)
        self.seconds["core"] += time.perf_counter() - started
        self.calls["core"] += 1
        return core


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
    for day in sorted(exams_on):
        status, part, _ = checker.check("day", frozenset({day}), exams_on[day], cap, portfolio)
        if part is None:
            LOG.debug("day %s failed: %s (%d exams)", day, status, len(exams_on[day]))
            failed.append(day)
        else:
            parts[frozenset({day})] = part
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
        if time.perf_counter() < checker.deadline:
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
    for group in groups:
        if time.perf_counter() >= checker.deadline:
            break
        if any(key & group and len(key) > 1 for key in parts):
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


def warm_start(checker: Checker, schedule: dict[str, str], rooms_used: set[str]) -> Parts | None:
    """Re-check an earlier verified placement in the current instance; usable only if every exam's
    earlier slot is still one of its candidates and its rooms still exist."""
    problem = checker.problem
    candidates = {item.exam_demand_id: set(item.candidate_slot_ids) for item in problem.demands}
    if set(schedule) != set(candidates) or any(schedule[exam] not in candidates[exam] for exam in candidates):
        LOG.debug("warm start not usable: the instance no longer allows every earlier placement")
        return None
    rooms = tuple(room for room in problem.rooms if room.room_id in rooms_used)
    if len(rooms) != len(rooms_used):
        LOG.debug("warm start not usable: rooms are missing")
        return None
    parts: Parts = {}
    for day, exams in sorted(by_day(problem, schedule).items()):
        part = checker.check("warm-start", frozenset({day}), exams, None, rooms, fixed=schedule)[1]
        if part is None:
            LOG.debug("warm start not usable: %s could not be re-checked", day)
            return None
        parts[frozenset({day})] = part
    return parts


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


def cost(problem: JointOptimizationInput, parts: list[Part]) -> tuple[int, int, int, int, int, int]:
    sessions = [row for part in parts for row in part.sessions]
    used = {row["room_id"] for row in sessions}
    rooms = {room.room_id: room for room in problem.rooms}
    pool = peak_staff(problem, sessions)
    room_cost = sum(rooms[room].annual_fixed_cost_ore for room in used)
    external = sum(rooms[row["room_id"]].external_session_cost_ore for row in sessions)
    pool_cost = problem.staffing.annual_cost_ore_per_staff * pool
    session_cost = problem.staffing.cost_ore_per_staff_session * sum(row["required_staff"] for row in sessions)
    return pool, room_cost, external, pool_cost, session_cost, room_cost + external + pool_cost + session_cost
