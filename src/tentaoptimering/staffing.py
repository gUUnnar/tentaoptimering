"""Anonymous but individually feasible invigilator plans for term sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True)
class StaffingStep:
    up_to_participants: int
    staff_required: int


@dataclass(frozen=True)
class WorkShift:
    shift_id: str
    start_minute: int
    end_minute: int


@dataclass(frozen=True)
class StaffingPolicy:
    ladder: tuple[StaffingStep, ...]
    shifts: tuple[WorkShift, ...]
    preparation_minutes: int
    closing_minutes: int
    minimum_break_minutes: int
    maximum_continuous_minutes: int
    maximum_daily_minutes: int
    minimum_daily_rest_minutes: int
    travel_minutes_between_buildings: int


@dataclass(frozen=True)
class StaffingTask:
    task_id: str
    scheduled_date: date
    start_minute: int
    end_minute: int
    building_id: str
    participants: int
    staff_required: int


@dataclass(frozen=True)
class StaffingPlan:
    feasible: bool
    worker_count: int
    work_minutes: int
    travel_minutes: int
    idle_minutes: int
    assignments: tuple[dict[str, object], ...]
    reason: str | None = None


def required_staff(participants: int, policy: StaffingPolicy) -> int:
    if participants <= 0:
        raise ValueError("Bemanningsuppgiften måste ha positiva deltagarantal.")
    for step in policy.ladder:
        if participants <= step.up_to_participants:
            return step.staff_required
    raise ValueError("Bemanningstrappan täcker inte salstillfällets deltagarantal.")


def plan_staffing(tasks: tuple[StaffingTask, ...], policy: StaffingPolicy) -> StaffingPlan:
    """Create a reproducible anonymous worker plan or identify an impossible task.

    Workers are created only when no prior worker can take an assignment. Long
    room-supervision duties are split into contiguous coverage segments no longer
    than the configured continuous-work limit. This keeps the room covered while
    requiring a real, recorded gap before an individual can return from a break.
    """
    _validate_policy(policy)
    workers: list[list[dict[str, object]]] = []
    travel_total = 0
    for task in _expanded_tasks(tasks, policy):
        start, end = task.start_minute, task.end_minute
        if not _fits_shift(start, end, policy.shifts):
            return StaffingPlan(False, len(workers), 0, travel_total, 0, (), f"task_outside_shift:{task.task_id}")
        for _ in range(task.staff_required):
            selection = _select_worker(workers, task, start, end, policy)
            if selection is None:
                workers.append([])
                selection = len(workers) - 1
            prior = workers[selection][-1] if workers[selection] else None
            travel = _travel_minutes(prior, task, policy)
            workers[selection].append({
                "staff_id": f"staff-{selection + 1}", "task_id": task.task_id,
                "scheduled_date": task.scheduled_date.isoformat(), "start_minute": start,
                "end_minute": end, "building_id": task.building_id,
                "travel_before_minutes": travel,
            })
            travel_total += travel
    assignments = tuple(item for worker in workers for item in worker)
    work_minutes = sum(int(item["end_minute"]) - int(item["start_minute"]) for item in assignments)
    idle_minutes = _idle_minutes(workers)
    return StaffingPlan(True, len(workers), work_minutes, travel_total, idle_minutes, assignments)


def _expanded_tasks(tasks: tuple[StaffingTask, ...], policy: StaffingPolicy) -> tuple[StaffingTask, ...]:
    """Turn a long supervised session into staff-covered break-sized duties."""
    expanded = []
    limit = min(policy.maximum_continuous_minutes, policy.maximum_daily_minutes)
    for task in tasks:
        start = task.start_minute - policy.preparation_minutes
        end = task.end_minute + policy.closing_minutes
        boundaries = list(range(start, end, limit)) + [end]
        for index, (segment_start, segment_end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
            task_id = task.task_id if len(boundaries) == 2 else f"{task.task_id}#{index}"
            expanded.append(StaffingTask(
                task_id, task.scheduled_date, segment_start, segment_end, task.building_id,
                task.participants, task.staff_required,
            ))
    return tuple(sorted(expanded, key=lambda item: (item.scheduled_date, item.start_minute, item.task_id)))


def _select_worker(workers: list[list[dict[str, object]]], task: StaffingTask, start: int, end: int, policy: StaffingPolicy) -> int | None:
    candidates = [
        index for index, assignments in enumerate(workers)
        if _can_assign(assignments, task, start, end, policy)
    ]
    return min(candidates, key=lambda index: (len(workers[index]), index)) if candidates else None


def _can_assign(assignments: list[dict[str, object]], task: StaffingTask, start: int, end: int, policy: StaffingPolicy) -> bool:
    if not assignments:
        return True
    prior = assignments[-1]
    previous_day = date.fromisoformat(str(prior["scheduled_date"]))
    previous_end = int(prior["end_minute"])
    if previous_day > task.scheduled_date:
        return False
    if previous_day < task.scheduled_date:
        return _rest_between(previous_day, previous_end, task.scheduled_date, start) >= policy.minimum_daily_rest_minutes
    travel = _travel_minutes(prior, task, policy)
    if previous_end + travel > start:
        return False
    day_assignments = [item for item in assignments if item["scheduled_date"] == task.scheduled_date.isoformat()]
    worked = sum(int(item["end_minute"]) - int(item["start_minute"]) for item in day_assignments)
    if worked + (end - start) > policy.maximum_daily_minutes:
        return False
    continuous_start = int(day_assignments[0]["start_minute"]) if day_assignments else start
    if start - previous_end >= policy.minimum_break_minutes:
        continuous_start = start
    return end - continuous_start <= policy.maximum_continuous_minutes


def _travel_minutes(prior: dict[str, object] | None, task: StaffingTask, policy: StaffingPolicy) -> int:
    if prior is None or str(prior["building_id"]) == task.building_id:
        return 0
    return policy.travel_minutes_between_buildings


def _rest_between(previous_day: date, previous_end: int, current_day: date, current_start: int) -> int:
    previous = datetime.combine(previous_day, time.min).replace(hour=previous_end // 60, minute=previous_end % 60)
    current = datetime.combine(current_day, time.min).replace(hour=current_start // 60, minute=current_start % 60)
    return int((current - previous).total_seconds() // 60)


def _fits_shift(start: int, end: int, shifts: tuple[WorkShift, ...]) -> bool:
    return any(shift.start_minute <= start and end <= shift.end_minute for shift in shifts)


def _idle_minutes(workers: list[list[dict[str, object]]]) -> int:
    return sum(
        max(0, int(right["start_minute"]) - int(left["end_minute"]))
        for assignments in workers
        for left, right in zip(assignments, assignments[1:])
        if left["scheduled_date"] == right["scheduled_date"]
    )


def _validate_policy(policy: StaffingPolicy) -> None:
    if not policy.ladder or not policy.shifts:
        raise ValueError("Bemanningspolicy kräver trappa och minst ett arbetspass.")
    if any(step.up_to_participants <= 0 or step.staff_required <= 0 for step in policy.ladder):
        raise ValueError("Bemanningstrappan måste ha positiva gränser och antal.")
    if [step.up_to_participants for step in policy.ladder] != sorted(step.up_to_participants for step in policy.ladder):
        raise ValueError("Bemanningstrappans deltagargränser måste vara stigande.")
    if any(shift.start_minute >= shift.end_minute for shift in policy.shifts):
        raise ValueError("Arbetspass måste sluta efter sin start.")
    values = (
        policy.preparation_minutes, policy.closing_minutes, policy.minimum_break_minutes,
        policy.maximum_continuous_minutes, policy.maximum_daily_minutes,
        policy.minimum_daily_rest_minutes, policy.travel_minutes_between_buildings,
    )
    if any(value < 0 for value in values) or policy.maximum_continuous_minutes == 0 or policy.maximum_daily_minutes == 0:
        raise ValueError("Bemanningspolicy har ogiltiga tidsvärden.")
