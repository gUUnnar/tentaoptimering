from __future__ import annotations

from datetime import date
import math
from typing import Any

import pandas as pd

from .optimizer_config import ScenarioConfig
from .optimizer_time import clock_minutes


def validate_solution(
    demands: pd.DataFrame,
    rooms: pd.DataFrame,
    assignments: pd.DataFrame,
    unplaced: pd.DataFrame,
    config: ScenarioConfig,
) -> dict[str, Any]:
    ready = demands.loc[
        demands["demand_input_status"].eq("ready_provisional_ladok_demand")
    ].copy()
    ready_by_id = ready.set_index("demand_id")
    room_by_id = rooms.set_index("room_id")
    placed_ids = set(assignments.get("demand_id", pd.Series(dtype=str)))
    unplaced_ids = set(unplaced.get("demand_id", pd.Series(dtype=str)))
    expected_ids = set(ready["demand_id"])
    errors: list[str] = []
    if placed_ids & unplaced_ids:
        errors.append("En efterfrågepost är både placerad och oplacerad.")
    if placed_ids | unplaced_ids != expected_ids:
        errors.append("Placerade och oplacerade poster täcker inte exakt körbar efterfrågan.")
    allowed_rooms = set(config.allowed_room_ids)
    used_rooms = set(assignments.get("room_id", pd.Series(dtype=str)))
    if used_rooms - allowed_rooms:
        errors.append("Resultatet använder rum som inte ingår i allowed_room_ids.")
    if not assignments.empty:
        for demand_id, group in assignments.groupby("demand_id", sort=False):
            source = ready_by_id.loc[demand_id]
            expected_seats = math.ceil(
                float(source["demand_value"]) * (1 + config.capacity_safety_margin_ratio)
            )
            if int(group["allocated_participants"].sum()) != expected_seats:
                errors.append(f"Efterfrågan summerar fel för {demand_id}.")
            if group["room_id"].nunique() > config.max_rooms_per_exam:
                errors.append(f"För många rum används för {demand_id}.")
            if not config.allow_split and group["room_id"].nunique() > 1:
                errors.append(f"Otillåten uppdelning för {demand_id}.")
            schedule = group[["scheduled_date", "start_time", "end_time"]].drop_duplicates()
            if len(schedule) != 1:
                errors.append(f"En efterfrågepost har flera schematider: {demand_id}.")
                continue
            item = schedule.iloc[0]
            original_date = date.fromisoformat(str(source["scheduled_date"]))
            assigned_date = date.fromisoformat(str(item["scheduled_date"]))
            day_shift = (assigned_date - original_date).days
            if not -config.date_shift_earlier_days <= day_shift <= config.date_shift_later_days:
                errors.append(f"Otillåten datumförflyttning för {demand_id}.")
            if assigned_date.isoweekday() not in config.allowed_weekdays:
                errors.append(f"Otillåten veckodag för {demand_id}.")
            start_shift = clock_minutes(str(item["start_time"])) - clock_minutes(
                str(source["booking_start_time"])
            )
            if abs(start_shift) > config.start_time_shift_minutes:
                errors.append(f"Otillåten starttidsförflyttning för {demand_id}.")
            if clock_minutes(str(item["start_time"])) < clock_minutes(config.earliest_start_time):
                errors.append(f"För tidig start för {demand_id}.")
            if clock_minutes(str(item["end_time"])) > clock_minutes(config.latest_end_time):
                errors.append(f"För sent slut för {demand_id}.")
            if config.enforce_historical_city:
                cities = {
                    value.strip()
                    for value in str(source.get("observed_cities") or "").split("|")
                    if value.strip()
                }
                assigned_cities = {
                    str(room_by_id.loc[room_id, "reference_city"])
                    for room_id in group["room_id"]
                }
                if cities and not assigned_cities.issubset(cities):
                    errors.append(f"Geografiskt otillåten placering för {demand_id}.")
        for (room_id, day), group in assignments.groupby(
            ["room_id", "scheduled_date"], sort=False
        ):
            capacity = int(room_by_id.loc[room_id, "capacity_seats"])
            minute_load = [0] * (24 * 60 + config.turnaround_minutes)
            minute_exams: list[set[str]] = [set() for _ in minute_load]
            for row in group.itertuples(index=False):
                start = clock_minutes(str(row.start_time))
                end = clock_minutes(str(row.end_time)) + config.turnaround_minutes
                for minute in range(start, end):
                    minute_load[minute] += int(row.allocated_participants)
                    minute_exams[minute].add(str(row.demand_id))
            if max(minute_load, default=0) > capacity:
                errors.append(f"Kapaciteten överskrids i {room_id} den {day}.")
            if not config.allow_co_location and any(len(values) > 1 for values in minute_exams):
                errors.append(f"Otillåten samlokalisering i {room_id} den {day}.")
    if errors:
        raise ValueError("Lösningsvalideringen misslyckades: " + " ".join(errors[:10]))
    return {
        "valid": True,
        "ready_demand_count": len(ready),
        "placed_demand_count": len(placed_ids),
        "unplaced_demand_count": len(unplaced_ids),
        "assignment_row_count": len(assignments),
        "checks": [
            "complete_demand_partition",
            "allowed_rooms",
            "capacity",
            "time_windows",
            "co_location",
            "split_limit",
            "historical_city",
        ],
    }

