from __future__ import annotations

from typing import Any

from .optimizer_config import ScenarioConfig


def historical_greedy_hint(
    demands: list[dict[str, Any]],
    rooms: dict[str, dict[str, Any]],
    config: ScenarioConfig,
) -> dict[str, Any]:
    """Build a deterministic feasible hint on original dates and times."""
    load: dict[tuple[str, str], list[int]] = {
        (room_id, day): [0] * (24 * 60 + config.turnaround_minutes)
        for room_id in rooms
        for day in {str(demand["scheduled_date"]) for demand in demands}
    }
    selected_options: dict[int, int] = {}
    allocations: dict[tuple[int, int, str], int] = {}
    unplaced: set[int] = set()
    priority = sorted(
        range(len(demands)),
        key=lambda index: (
            config.objective_weights["unplaced_exams"]
            + demands[index]["required_demand"]
            * config.objective_weights["unplaced_participants"],
            demands[index]["required_demand"],
            str(demands[index]["demand_id"]),
        ),
        reverse=True,
    )
    for demand_index in priority:
        demand = demands[demand_index]
        original = next(
            (
                (option_index, option)
                for option_index, option in enumerate(demand["options"])
                if option["is_historical_time"]
            ),
            None,
        )
        if original is None:
            unplaced.add(demand_index)
            continue
        option_index, option = original
        room_residuals: list[tuple[int, str]] = []
        for room_id, room in rooms.items():
            if config.enforce_historical_city and demand["historical_cities"]:
                if str(room["reference_city"]) not in demand["historical_cities"]:
                    continue
            minute_loads = load[room_id, option["date"]]
            overlap = minute_loads[option["start"] : option["occupancy_end"]]
            if not overlap:
                continue
            if not config.allow_co_location and max(overlap, default=0) > 0:
                residual = 0
            else:
                residual = int(room["capacity_seats"]) - max(overlap, default=0)
            room_residuals.append((max(0, residual), room_id))
        room_residuals.sort(reverse=True)
        room_limit = config.max_rooms_per_exam if config.allow_split else 1
        candidates = room_residuals[:room_limit]
        if sum(residual for residual, _ in candidates) < demand["required_demand"]:
            unplaced.add(demand_index)
            continue
        remaining = demand["required_demand"]
        selected_options[demand_index] = option_index
        for residual, room_id in candidates:
            allocated = min(residual, remaining)
            if allocated <= 0:
                continue
            allocations[demand_index, option_index, room_id] = allocated
            minute_loads = load[room_id, option["date"]]
            for minute in range(option["start"], option["occupancy_end"]):
                minute_loads[minute] += allocated
            remaining -= allocated
            if remaining == 0:
                break
    return {
        "selected_options": selected_options,
        "allocations": allocations,
        "unplaced": unplaced,
    }

