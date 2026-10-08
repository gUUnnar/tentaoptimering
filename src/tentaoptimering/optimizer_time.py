from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from .optimizer_config import ScenarioConfig


def clock_minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def clock_text(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def duration_minutes(value: str) -> int:
    start_text, end_text = value.split("-", maxsplit=1)
    start = clock_minutes(start_text)
    end = clock_minutes(end_text)
    if end <= start:
        end += 24 * 60
    return end - start


def _time_shifts(maximum: int, step: int) -> list[int]:
    values = set(range(-maximum, maximum + 1, step))
    values.add(0)
    return sorted(values)


def options_for_demand(row: pd.Series, config: ScenarioConfig) -> list[dict[str, Any]]:
    original_date = date.fromisoformat(str(row["scheduled_date"]))
    original_start = clock_minutes(str(row["booking_start_time"]))
    duration = duration_minutes(str(row["scheduled_time"]))
    earliest = clock_minutes(config.earliest_start_time)
    latest = clock_minutes(config.latest_end_time)
    options: list[dict[str, Any]] = []
    for day_shift in range(-config.date_shift_earlier_days, config.date_shift_later_days + 1):
        candidate_date = original_date + timedelta(days=day_shift)
        if candidate_date.isoweekday() not in config.allowed_weekdays:
            continue
        for minute_shift in _time_shifts(
            config.start_time_shift_minutes, config.start_time_step_minutes
        ):
            start = original_start + minute_shift
            end = start + duration
            if start < earliest or end > latest:
                continue
            options.append(
                {
                    "date": candidate_date.isoformat(),
                    "start": start,
                    "end": end,
                    "occupancy_end": end + config.turnaround_minutes,
                    "duration": duration,
                    "day_shift": day_shift,
                    "minute_shift": minute_shift,
                    "is_historical_time": day_shift == 0 and minute_shift == 0,
                }
            )
    return options


def historical_capacity_check(
    demands: list[dict[str, Any]],
    rooms: dict[str, dict[str, Any]],
    enforce_historical_city: bool,
) -> dict[str, Any]:
    capacity_by_city: dict[str, int] = {}
    for room in rooms.values():
        city = str(room["reference_city"]) if enforce_historical_city else "__all__"
        capacity_by_city[city] = capacity_by_city.get(city, 0) + int(room["capacity_seats"])
    events: dict[tuple[str, str], list[tuple[int, int, int]]] = {}
    for demand in demands:
        cities = demand["historical_cities"]
        city = next(iter(cities)) if enforce_historical_city and len(cities) == 1 else "__all__"
        start = clock_minutes(str(demand["booking_start_time"]))
        end = start + duration_minutes(str(demand["scheduled_time"]))
        events.setdefault((city, str(demand["scheduled_date"])), []).append(
            (start, end, int(demand["required_demand"]))
        )
    peak = 0
    maximum_shortfall = 0
    peak_context: dict[str, Any] | None = None
    for (city, day), intervals in events.items():
        boundaries = sorted({value for start, end, _ in intervals for value in (start, end)})
        capacity = capacity_by_city.get(city, 0)
        for segment_start, segment_end in zip(boundaries, boundaries[1:]):
            load = sum(
                seats
                for start, end, seats in intervals
                if start < segment_end and end > segment_start
            )
            shortfall = max(0, load - capacity)
            if load > peak:
                peak = load
                peak_context = {
                    "city": city,
                    "scheduled_date": day,
                    "start_time": clock_text(segment_start),
                    "end_time": clock_text(segment_end),
                    "required_seats": load,
                    "scenario_capacity": capacity,
                }
            maximum_shortfall = max(maximum_shortfall, shortfall)
    return {
        "input_peak_concurrent_required_seats": peak,
        "maximum_aggregate_capacity_shortfall": maximum_shortfall,
        "input_peak_context": peak_context,
    }

