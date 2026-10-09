"""Independent checks for persisted anonymous invigilator assignments."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any

import pandas as pd

from .staffing import required_staff
from .term_calendar import CalendarSlot

if TYPE_CHECKING:
    from .integrated_config import IntegratedTermScenario


PASS = "pass"
FAIL = "fail"
NOT_EVALUATED = "not_evaluated"


def validate_staffing(
    allocations: pd.DataFrame, staff_rows: pd.DataFrame | None, demands: dict[str, dict[str, Any]],
    rooms: dict[str, dict[str, Any]], scenario: IntegratedTermScenario,
    slots: dict[str, CalendarSlot],
) -> tuple[str, str, tuple[str, ...]]:
    """Validate saved work assignments; never call the staff-planning algorithm."""
    if staff_rows is None:
        return NOT_EVALUATED, "Körningen saknar sparade individuella vaktuppgifter.", ()
    required_columns = {"staff_id", "task_id", "scheduled_date", "start_minute", "end_minute", "building_id", "travel_before_minutes"}
    if not required_columns.issubset(staff_rows.columns):
        return NOT_EVALUATED, "Vaktuppgiftsartefakten saknar obligatoriska kolumner.", tuple(sorted(required_columns - set(staff_rows.columns)))
    expected = _expected_tasks(allocations, demands, rooms, scenario, slots)
    if isinstance(expected, tuple):
        return FAIL, "Bemanningstrappan täcker inte ett salstillfälle.", expected
    failures = _task_coverage(staff_rows, expected)
    failures.extend(_worker_sequences(staff_rows, scenario))
    if failures:
        return FAIL, "Sparade vaktuppgifter bryter mot aktiv bemannings- eller arbetstidsregel.", tuple(sorted(set(failures)))
    return PASS, "Sparade vaktuppgifter uppfyller aktiv trappa, pass, raster, vila och reseregler.", ()


def _expected_tasks(
    allocations: pd.DataFrame, demands: dict[str, dict[str, Any]], rooms: dict[str, dict[str, Any]],
    scenario: IntegratedTermScenario, slots: dict[str, CalendarSlot],
) -> dict[str, dict[str, object]] | tuple[str, ...]:
    expected: dict[str, dict[str, object]] = {}
    for (room_id, slot_id), rows in allocations.groupby(["room_id", "slot_id"]):
        slot = slots.get(str(slot_id))
        room = rooms.get(str(room_id))
        members = [demands.get(str(item)) for item in rows["exam_demand_id"]]
        if slot is None or room is None or any(item is None for item in members):
            continue
        participants = int(rows["participants"].sum())
        try:
            count = required_staff(participants, scenario.staffing_policy)
        except ValueError:
            return (f"{room_id}|{slot_id}",)
        duration = max(int(item["duration_minutes"]) for item in members if item)
        base_id = f"{room_id}|{slot_id}"
        start = slot.start_minute - scenario.staffing_policy.preparation_minutes
        end = slot.start_minute + duration + max(
            scenario.staffing_policy.closing_minutes, scenario.calendar.turnaround_minutes,
        )
        limit = min(scenario.staffing_policy.maximum_continuous_minutes, scenario.staffing_policy.maximum_daily_minutes)
        boundaries = list(range(start, end, limit)) + [end]
        for index, (segment_start, segment_end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
            task_id = base_id if len(boundaries) == 2 else f"{base_id}#{index}"
            expected[task_id] = {
                "scheduled_date": slot.scheduled_date.isoformat(), "start_minute": segment_start,
                "end_minute": segment_end, "building_id": str(room.get("building_id") or room_id),
                "count": count,
            }
    return expected


def _task_coverage(rows: pd.DataFrame, expected: dict[str, dict[str, object]]) -> list[str]:
    failures: list[str] = []
    for task_id, task in expected.items():
        matching = rows.loc[rows["task_id"].astype(str) == task_id]
        if len(matching) != task["count"]:
            failures.append(f"staffing_count:{task_id}")
            continue
        for row in matching.itertuples(index=False):
            if (
                str(row.scheduled_date) != task["scheduled_date"]
                or not _integer_equal(row.start_minute, task["start_minute"])
                or not _integer_equal(row.end_minute, task["end_minute"])
                or str(row.building_id) != task["building_id"]
                or not str(row.staff_id).strip()
            ):
                failures.append(f"staffing_task:{task_id}")
    expected_ids = set(expected)
    failures.extend(f"staffing_unknown_task:{value}" for value in rows["task_id"].astype(str) if value not in expected_ids)
    return failures


def _worker_sequences(rows: pd.DataFrame, scenario: IntegratedTermScenario) -> list[str]:
    failures: list[str] = []
    policy = scenario.staffing_policy
    for staff_id, group in rows.groupby("staff_id"):
        records = sorted(group.to_dict("records"), key=lambda item: (str(item["scheduled_date"]), int(item["start_minute"])))
        daily_minutes: dict[str, int] = {}
        continuous_start: int | None = None
        previous: dict[str, object] | None = None
        for record in records:
            start, end = _int(record.get("start_minute")), _int(record.get("end_minute"))
            day_text = str(record.get("scheduled_date"))
            if start is None or end is None or end <= start or not _fits_shift(start, end, scenario):
                failures.append(f"staffing_shift:{staff_id}")
                previous = record
                continue
            daily_minutes[day_text] = daily_minutes.get(day_text, 0) + end - start
            if daily_minutes[day_text] > policy.maximum_daily_minutes:
                failures.append(f"staffing_daily_work:{staff_id}|{day_text}")
            if previous is not None:
                previous_day = str(previous["scheduled_date"])
                previous_end = _int(previous.get("end_minute"))
                if previous_end is None:
                    failures.append(f"staffing_time:{staff_id}")
                elif previous_day == day_text:
                    travel = 0 if str(previous["building_id"]) == str(record["building_id"]) else policy.travel_minutes_between_buildings
                    if previous_end + travel > start or _int(record.get("travel_before_minutes")) != travel:
                        failures.append(f"staffing_travel_or_overlap:{staff_id}|{day_text}")
                    if start - previous_end >= policy.minimum_break_minutes:
                        continuous_start = start
                else:
                    if _rest(previous_day, previous_end, day_text, start) < policy.minimum_daily_rest_minutes:
                        failures.append(f"staffing_rest:{staff_id}|{day_text}")
                    continuous_start = start
            if continuous_start is None:
                continuous_start = start
            if end - continuous_start > policy.maximum_continuous_minutes:
                failures.append(f"staffing_break:{staff_id}|{day_text}")
            previous = record
    return failures


def _fits_shift(start: int, end: int, scenario: IntegratedTermScenario) -> bool:
    return any(item.start_minute <= start and end <= item.end_minute for item in scenario.staffing_policy.shifts)


def _rest(previous_day: str, previous_end: int, current_day: str, current_start: int) -> int:
    earlier = datetime.combine(date.fromisoformat(previous_day), time.min).replace(hour=previous_end // 60, minute=previous_end % 60)
    later = datetime.combine(date.fromisoformat(current_day), time.min).replace(hour=current_start // 60, minute=current_start % 60)
    return int((later - earlier).total_seconds() // 60)


def _integer_equal(value: object, expected: object) -> bool:
    return _int(value) == expected


def _int(value: object) -> int | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return int(numeric) if numeric.is_integer() else None
