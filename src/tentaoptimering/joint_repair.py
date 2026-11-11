"""The smallest change that makes a run possible.

A run without a solution tells the user only that it does not fit. This module searches for a way forward: the fewest changes,
among the settings the user has allowed us to touch (the calendar and dates, and the fixed bookings), after which the solver
finds a solution. Nothing is saved and the user's scenario is never changed; the answer is a set of parameter values that the
interface can put into the form.

Two steps, each with its own check:

A. *Exams without any allowed occasion.* This needs no solving: the problem is rebuilt with a candidate move and the exams
   that have no occasion are counted. Moves are taken greedily (the one that frees the most exams), then every move is
   dropped in turn and kept out if the count stays zero, so the set cannot be made smaller by removing one of its moves.
B. *Capacity.* With the moves of step A the solver gets a short time. If it proves that the exams do not fit, the fixed-booking
   moves are tried one at a time, the smallest group first; if none is enough alone, all together, and then each is dropped in
   turn as long as the solver still finds a solution. A solution is the only thing that counts as possible: a probe that
   finds neither a solution nor a proof is reported as undecided, never as success.

The result is minimal among the moves that were tried (the answer says which), not among every conceivable change.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
import threading
import time
from typing import Any

from .app_paths import bundled_joint_catalog_path
from .app_storage import AppStorage
from .joint_api import JointRunRequest, run_config
from .joint_inputs import build_real_subset_problem
from .joint_optimizer import solve_joint_optimization
from .joint_repair_text import (
    EXPLORATIVE, NO_BLOCK_LABEL, POLICY_LABEL, calendar_label, remove_group_label, start_time_label, weekday_label, window_label,
)
from .joint_scenarios import effective_changes, merge_changes, read_scenario, scenario_values, write_run_snapshot
from .joint_strategy.resources import CancelToken, ExecutionBudget
from .parameter_catalog import load_parameter_catalog

PROBE_SECONDS = 20.0
LONG_SECONDS = 90.0   # a probe that was undecided gets one longer try
TOTAL_SECONDS = 420.0
WINDOW_STEPS = (1, 2, 3, 7)
FOUND, NOTHING_NEEDED, NOT_FOUND, INCOMPLETE, UNPROVEN = "found", "nothing_needed", "not_found", "incomplete", "unproven"
SOLUTION, INFEASIBLE, UNDECIDED = "solution", "infeasible", "undecided"


@dataclass(frozen=True)
class Move:
    """One change that the suggestion may contain: what it sets, how it is worded and whether it makes the result explorative."""

    move_id: str
    kind: str                    # weekday | start_time | calendar | window | policy | fixed_bookings
    label: str
    value: Any = None            # the added weekday, the clock time, the date, the number of days or the parameter of a fixed-booking group
    side: str = ""
    explorative: bool = False


class RepairProgress:
    """How far a search has come; read from the status route while the job runs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {"done": 0, "current": None}

    def start(self, label: str) -> None:
        with self._lock:
            self._state["current"] = label

    def finish(self) -> None:
        with self._lock:
            self._state["done"] += 1
            self._state["current"] = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)


@dataclass
class _Evaluation:
    blocked: int
    must_move: int
    problem: Any
    outcome: str | None = None
    seconds: float | None = None


@dataclass
class _Search:
    storage: AppStorage
    content: dict[str, Any]
    catalog_file: Any
    cancel: CancelToken
    progress: RepairProgress | None
    started: float = field(default_factory=time.perf_counter)
    attempts: list[dict[str, Any]] = field(default_factory=list)

    def out_of_time(self) -> bool:
        return self.cancel.cancelled or time.perf_counter() - self.started > TOTAL_SECONDS

    def evaluate(self, extra: dict[str, Any], label: str, solve: bool = False, seconds: float = PROBE_SECONDS) -> _Evaluation:
        if self.progress:
            self.progress.start(label)
        try:
            effective_changes(load_parameter_catalog(self.catalog_file), self.content, extra)  # a bad value is refused, not tried
            path = write_run_snapshot(self.storage, merge_changes(self.content, extra))
            try:
                problem = build_real_subset_problem(path, self.storage.processed_dir, self.catalog_file)
            finally:
                path.unlink(missing_ok=True)
            blocked = [item for item in problem.demands if not item.candidate_slot_ids]
            must_move = [item for item in problem.demands if item.candidate_slot_ids and item.original_slot_id not in item.candidate_slot_ids]
            result = _Evaluation(len(blocked), len(must_move), problem)
            if solve and not blocked:
                short = replace(problem, solver=replace(problem.solver, time_limit_seconds=seconds))
                solved = solve_joint_optimization(short, None, ExecutionBudget(), self.cancel, None, None)
                outcome = solved.solver.outcome
                result.outcome = SOLUTION if outcome in ("optimal", "feasible_not_proven") else INFEASIBLE if outcome == "infeasible" else UNDECIDED
                result.seconds = round(solved.solver.wall_time_seconds, 1)
            self.attempts.append({"label": label, "exams_without_occasion": result.blocked, "outcome": result.outcome, "seconds": result.seconds})
            return result
        finally:
            if self.progress:
                self.progress.finish()


def _apply(extra: dict[str, Any], moves: list[Move], values: dict[str, Any]) -> dict[str, Any]:
    """The parameter values that a set of moves gives (weekdays and start times are added to, calendar dates and window days widened)."""
    out: dict[str, Any] = {}
    for move in moves:
        if move.kind == "weekday":
            current = set(out.get("calendar.weekdays", values["calendar.weekdays"]))
            out["calendar.weekdays"] = sorted(current | {int(move.value)})
        elif move.kind == "start_time":
            current = list(out.get("calendar.start_times", values["calendar.start_times"]))
            out["calendar.start_times"] = sorted(set(current) | {str(move.value)})
        elif move.kind == "calendar":
            side, day = move.value
            key = "calendar.start_date" if side == "start" else "calendar.end_date"
            old = out.get(key) or values.get(key)
            out[key] = day if not old else (min(old, day) if side == "start" else max(old, day))
        elif move.kind == "window":
            side, days = move.value
            key = f"window.{side}_days"
            out[key] = max(int(out.get(key, values[key])), int(days))
        elif move.kind == "policy":
            out["wish.candidate_policy"] = str(move.value)
        elif move.kind == "fixed_bookings":
            if move.value == "reservations.policy":
                out["reservations.policy"] = "none"
            else:
                out[str(move.value)] = "remove"
    return {**extra, **out}


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _calendar_moves(evaluation: _Evaluation, values: dict[str, Any], chosen: list[Move]) -> list[list[Move]]:
    """Candidate moves for the exams that have no occasion, in tiers: the targeted ones first, the general widening after them."""
    problem = evaluation.problem
    blocked = [item for item in problem.demands if not item.candidate_slot_ids]
    taken = {move.move_id for move in chosen}
    weekdays = {int(day) for day in values["calendar.weekdays"]}
    starts = {str(item) for item in values["calendar.start_times"]}
    targeted: list[Move] = []
    days = sorted({item.original_date.isoweekday() for item in blocked if item.original_date} | {
        date.fromisoformat(str(text)).isoweekday() for item in blocked for text in item.wish_dates if text and str(text) != "None"} - weekdays,
        key=lambda day: (day >= 6, day))  # a weekend day is the last resort among the weekdays
    targeted += [Move(f"weekday:{day}", "weekday", weekday_label(day), day) for day in days]
    clocks = sorted({_hhmm(item.original_start_minute) for item in blocked if item.original_start_minute is not None} - starts)
    targeted += [Move(f"start_time:{clock}", "start_time", start_time_label(clock), clock) for clock in clocks]
    first = min((item.original_date for item in blocked if item.original_date), default=None)
    last = max((item.original_date for item in blocked if item.original_date), default=None)
    if first and values.get("calendar.start_date") and str(values["calendar.start_date"]) > first.isoformat():
        targeted.append(Move("calendar:start", "calendar", calendar_label("start", first.isoformat()), ("start", first.isoformat())))
    if last and values.get("calendar.end_date") and str(values["calendar.end_date"]) < last.isoformat():
        targeted.append(Move("calendar:end", "calendar", calendar_label("end", last.isoformat()), ("end", last.isoformat())))
    general: list[Move] = []
    if str(values.get("wish.candidate_policy")) == "wishes":
        general.append(Move("policy", "policy", POLICY_LABEL, "wishes_and_window"))
    for side in ("earlier", "later"):
        general += [Move(f"window:{side}:{days}", "window", window_label(side, days), (side, days))
                    for days in WINDOW_STEPS if days > int(values[f"window.{side}_days"])]
    return [[move for move in tier if move.move_id not in taken] for tier in (targeted, general)]


def _fixed_booking_moves(problem: Any, values: dict[str, Any]) -> list[Move]:
    """The fixed-booking groups that still block a room, the smallest first, and finally no blocking at all."""
    basis = ((problem.resource_basis or {}).get("reservations")) or {}
    if basis.get("status") != "read" or values.get("reservations.policy") == "none":
        return []
    groups = [item for item in basis.get("groups", []) if item.get("bookings") and item.get("action") != "remove"]
    moves = [Move(f"fixed:{item['action_parameter']}", "fixed_bookings", remove_group_label(item["action_parameter"], int(item["bookings"])),
                  item["action_parameter"], EXPLORATIVE, True) for item in sorted(groups, key=lambda item: int(item["bookings"]))]
    if moves:
        moves.append(Move("fixed:none", "fixed_bookings", NO_BLOCK_LABEL, "reservations.policy", EXPLORATIVE, True))
    return moves


def suggest_fix(storage: AppStorage, request: JointRunRequest, progress: RepairProgress | None, cancel: CancelToken,
                catalog_path: Any = None, scenarios_dir: Any = None) -> dict[str, Any]:
    """Search for the smallest set of allowed changes after which the solver finds a solution (see the module text)."""
    catalog_file = catalog_path or bundled_joint_catalog_path()
    config, snapshot = run_config(storage, request, scenarios_dir, catalog_file)
    try:
        content = read_scenario(config)
    finally:
        if snapshot is not None:
            snapshot.unlink(missing_ok=True)
    if content is None:
        raise FileNotFoundError("Scenariot går inte att läsa.")
    search = _Search(storage, content, catalog_file, cancel, progress)
    base = search.evaluate({}, "Prövar inställningarna som de är", solve=True)
    values = {item.parameter_id: item.value for item in base.problem.parameters}
    if base.blocked == 0 and base.outcome == SOLUTION:
        return _answer(NOTHING_NEEDED, [], {}, base, base, search, "Inställningarna går redan att lösa; inget behöver ändras.")
    chosen: list[Move] = []
    current = base
    # Step A: give every exam an occasion.
    while current.blocked > 0 and not search.out_of_time():
        best: tuple[int, Move, _Evaluation] | None = None
        for index, tier in enumerate(_calendar_moves(current, values, chosen)):
            for move in tier:
                trial = search.evaluate(_apply({}, chosen + [move], values), f"Prövar: {move.label}")
                gain = current.blocked - trial.blocked
                if gain > 0 and (best is None or gain > best[0]):
                    best = (gain, move, trial)
                    if index == 1:
                        break  # the general moves are listed from the least to the most disturbing: the first that helps is the smallest
            if best:
                break
        if best is None:
            break
        chosen.append(best[1])
        current = best[2]
    if current.blocked > 0:
        return _answer(NOT_FOUND if not search.out_of_time() else INCOMPLETE, chosen, _apply({}, chosen, values), base, current, search,
                       f"{current.blocked} tentor har fortfarande inget tillåtet tillfälle med de ändringar som får föreslås (kalender och fasta bokningar).")
    for move in list(chosen):  # drop what is not needed: the set must not be reducible by one move
        if search.out_of_time():
            break
        rest = [item for item in chosen if item is not move]
        if search.evaluate(_apply({}, rest, values), f"Kontrollerar att '{move.label}' behövs").blocked == 0:
            chosen = rest
    solved = search.evaluate(_apply({}, chosen, values), "Prövar förslaget med solvern", solve=True) if chosen else base
    # Step B: capacity.
    if solved.outcome != SOLUTION:
        extras = _fixed_booking_moves(solved.problem, values)
        found: list[Move] | None = None
        undecided: list[Move] = []
        for move in extras:
            if search.out_of_time():
                break
            trial = search.evaluate(_apply({}, chosen + [move], values), f"Prövar: {move.label}", solve=True)
            if trial.outcome == SOLUTION:
                found, solved = [move], trial
                break
            if trial.outcome == UNDECIDED:
                undecided.append(move)
        for move in undecided:  # not proven impossible: one longer try for the smallest such candidate
            if found is not None or time.perf_counter() - search.started > TOTAL_SECONDS - LONG_SECONDS or search.cancel.cancelled:
                continue
            trial = search.evaluate(_apply({}, chosen + [move], values), f"Prövar längre: {move.label}", solve=True, seconds=LONG_SECONDS)
            if trial.outcome == SOLUTION:
                found, solved = [move], trial
            break
        groups = [move for move in extras if move.value != "reservations.policy"]
        blanket = [move for move in extras if move.value == "reservations.policy"]
        for combo, label in ((groups if len(groups) > 1 else [], "Prövar att ta bort alla grupper"), (blanket, "Prövar att ta bort alla fasta bokningar")):
            if found is not None or not combo or search.out_of_time():
                continue
            trial = search.evaluate(_apply({}, chosen + combo, values), label, solve=True)
            if trial.outcome == SOLUTION:
                found, solved = list(combo), trial
                for move in list(found):  # keep only what the solver still needs
                    if search.out_of_time() or len(found) == 1:
                        break
                    rest = [item for item in found if item is not move]
                    again = search.evaluate(_apply({}, chosen + rest, values), f"Kontrollerar att '{move.label}' behövs", solve=True)
                    if again.outcome == SOLUTION:
                        found, solved = rest, again
        if found is None and undecided:
            move = undecided[0]  # the smallest change that the solver could not prove impossible
            return _answer(UNPROVEN, chosen + [move], _apply({}, chosen + [move], values), base, solved, search,
                           f"Ingen lösning hittades ännu, men solvern kunde inte bevisa att det är omöjligt med '{move.label}'. Förslaget är oprövat: kör med längre tid för att se om en lösning finns.")
        if found is None:
            status = INCOMPLETE if search.out_of_time() else NOT_FOUND
            return _answer(status, chosen, _apply({}, chosen, values), base, solved, search,
                           "Ingen lösning hittades med de ändringar som får föreslås (kalender och fasta bokningar). Orsaken kan vara salarnas kapacitet.")
        chosen += found
    return _answer(FOUND, chosen, _apply({}, chosen, values), base, solved, search,
                   f"Solvern hittade en lösning med {len(chosen)} {'ändring' if len(chosen) == 1 else 'ändringar'}.")


def _answer(status: str, chosen: list[Move], parameters: dict[str, Any], base: _Evaluation, last: _Evaluation, search: _Search, text: str) -> dict[str, Any]:
    explorative = any(move.explorative for move in chosen)
    return {
        "kind": "joint_repair", "status": status, "summary": text, "parameters": deepcopy(parameters),
        "steps": [{"id": move.move_id, "label": move.label, "side_effect": move.side or None} for move in chosen],
        "explorative": explorative,
        "verified": {"outcome": last.outcome, "seconds": last.seconds} if status == FOUND else None,
        "exams_without_occasion": {"before": base.blocked, "after": last.blocked},
        "searched": ["Kalender och datum", "Fasta bokningar"],
        "note": "Förslaget är det minsta som hittades bland de ändringar som prövades (kalender, datum och fasta bokningar); andra ändringar, till exempel fler salar, prövas inte.",
        "attempts": search.attempts, "seconds": round(time.perf_counter() - search.started, 1),
    }
