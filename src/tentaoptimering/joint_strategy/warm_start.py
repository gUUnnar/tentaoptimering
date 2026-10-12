"""Warm start: an earlier placement is reused only where it fits the current instance, and always re-checked.

An earlier placement (exam -> slot, and the rooms it used) is never trusted. It becomes a first upper
bound only if, in the *current* instance, every exam still has its earlier slot as a candidate and every
day passes the exact joint check with that slot fixed (room capacity, digital compatibility, planning
area, buildings, conflicts, turnaround, staffing). Cost, pool and room portfolio are recomputed from the
re-checked placement under the current prices, so a changed cost parameter changes the cost, not the
decision. Whatever cannot be reused whole is still offered to the relaxation as a search hint, for the
exams whose earlier slot is still allowed.

`StartReport` records what happened and why, in the vocabulary of the saved run artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import logging
import time
from typing import Any

from ..joint_contract import JointOptimizationInput
from .verification import Checker, Parts, Request, by_day

LOG = logging.getLogger(__name__)

NOT_PROVIDED = "not_provided"
ACCEPTED = "accepted"
REJECTED = "rejected"
HINT_ONLY = "hint_only"

WARM_START_SHARE = 0.5      # of the run's time limit that the re-check of a warm start may use
MAX_REASONS = 6


@dataclass
class StartReport:
    """What happened to an earlier placement, and how fast the first verified solution came."""

    status: str = NOT_PROVIDED
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    exams_in_start: int = 0
    exams_reused: int = 0
    exams_without_start: int = 0
    exams_not_allowed: int = 0
    exams_outside_instance: int = 0
    rooms_in_start: int = 0
    rooms_missing: list[str] = field(default_factory=list)
    days_checked: int = 0
    days_failed: int = 0
    check_seconds: float | None = None
    verified_cost_ore: int | None = None
    hint_exams: int = 0
    first_solution_seconds: float | None = None
    first_solution_source: str | None = None
    final_cost_ore: int | None = None
    final_source: str | None = None
    interrupted: bool = False

    def reject(self, reason: str) -> None:
        self.status = REJECTED
        self.reasons.append(reason)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fit:
    """How an earlier placement fits the current instance."""

    schedule: dict[str, str]        # earlier slot of each current exam that still allows it
    without_start: tuple[str, ...]  # current exams the earlier placement did not cover
    not_allowed: tuple[str, ...]    # current exams whose earlier slot is no longer a candidate
    outside: tuple[str, ...]        # earlier exams that are not in the current instance
    rooms: tuple[str, ...]          # earlier rooms that still exist
    rooms_missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.without_start and not self.not_allowed and bool(self.rooms)


def fit(problem: JointOptimizationInput, schedule: dict[str, str], rooms_used: set[str]) -> Fit:
    candidates = {item.exam_demand_id: set(item.candidate_slot_ids) for item in problem.demands}
    reusable = {exam: schedule[exam] for exam in sorted(candidates) if exam in schedule and schedule[exam] in candidates[exam]}
    existing = {room.room_id for room in problem.rooms}
    return Fit(
        schedule=reusable,
        without_start=tuple(sorted(exam for exam in candidates if exam not in schedule)),
        not_allowed=tuple(sorted(exam for exam in candidates if exam in schedule and schedule[exam] not in candidates[exam])),
        outside=tuple(sorted(exam for exam in schedule if exam not in candidates)),
        rooms=tuple(sorted(rooms_used & existing)),
        rooms_missing=tuple(sorted(rooms_used - existing)),
    )


def warm_start(
    checker: Checker, schedule: dict[str, str], rooms_used: set[str], report: StartReport | None = None,
) -> tuple[Parts | None, dict[str, str]]:
    """Re-check an earlier placement in the current instance.

    Returns the verified parts (None if it cannot be used whole) and the earlier slots that are still
    allowed, which are worth giving to the relaxation as a hint either way.
    """
    report = report if report is not None else StartReport()
    problem = checker.problem
    found = fit(problem, schedule, rooms_used)
    report.exams_in_start, report.exams_reused = len(schedule), len(found.schedule)
    report.exams_without_start, report.exams_not_allowed = len(found.without_start), len(found.not_allowed)
    report.exams_outside_instance, report.rooms_in_start = len(found.outside), len(rooms_used)
    report.rooms_missing = list(found.rooms_missing)
    report.hint_exams = len(found.schedule)
    if found.without_start:
        report.reject(f"{len(found.without_start)} tentor i den nya instansen saknar tidigare placering ({_names(found.without_start)}).")
    if found.not_allowed:
        report.reject(f"{len(found.not_allowed)} tentors tidigare pass tillåts inte längre ({_names(found.not_allowed)}).")
    if not found.rooms:
        report.reject("Ingen av de tidigare använda salarna finns kvar i den nya instansen.")
    if not found.complete:
        LOG.debug("warm start not usable: %s", "; ".join(report.reasons))
        return None, found.schedule
    if found.rooms_missing:
        report.notes.append(f"Salar som saknas i den nya instansen: {_names(found.rooms_missing)}; kontrollen görs med återstående salar.")
    rooms = tuple(room for room in problem.rooms if room.room_id in found.rooms)
    days = sorted(by_day(problem, found.schedule).items())
    started = time.perf_counter()
    with checker.until(WARM_START_SHARE * problem.solver.time_limit_seconds):
        outcomes = checker.check_many([
            Request("warm-start", frozenset({day}), exams, None, rooms, fixed=found.schedule) for day, exams in days
        ])
    report.check_seconds = time.perf_counter() - started
    report.days_checked = len(days)
    failed = [(day, status) for (day, _), (status, part, _) in zip(days, outcomes) if part is None]
    report.days_failed = len(failed)
    if failed and checker.cancel.cancelled:
        report.interrupted = True
        report.reject("Körningen avbröts under kontrollen av den tidigare placeringen.")
        return None, found.schedule
    if failed:
        for day, status in failed[:MAX_REASONS]:
            report.reject(_day_reason(day, status))
        if len(failed) > MAX_REASONS:
            report.reasons.append(f"… och {len(failed) - MAX_REASONS} dagar till.")
        LOG.debug("warm start not usable: %d of %d days failed the re-check", len(failed), len(days))
        return None, found.schedule
    return {frozenset({day}): part for (day, _), (_, part, _) in zip(days, outcomes)}, found.schedule


def _day_reason(day: date, status: str) -> str:
    if status == "infeasible":
        return f"{day.isoformat()}: tentorna ryms inte längre på dagen enligt de nya reglerna (bevisat ogenomförbart)."
    return f"{day.isoformat()}: kontrollen hann inte avgöras inom varmstartens tidsandel."


def _names(items: tuple[str, ...], limit: int = 3) -> str:
    return ", ".join(items[:limit]) + (f" m.fl." if len(items) > limit else "")
