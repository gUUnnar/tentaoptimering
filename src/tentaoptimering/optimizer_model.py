from __future__ import annotations

from dataclasses import dataclass, replace
import math
from time import perf_counter
from typing import Any

from ortools.sat.python import cp_model
import pandas as pd

from .optimizer_config import ScenarioConfig
from .optimizer_hint import historical_greedy_hint
from .optimizer_time import clock_text, historical_capacity_check, options_for_demand


@dataclass(frozen=True)
class OptimizationResult:
    solver_status: str
    solver_status_code: int
    runtime_seconds: float
    objective_value: float | None
    best_objective_bound: float | None
    relative_gap: float | None
    assignments: pd.DataFrame
    unplaced: pd.DataFrame
    metrics: dict[str, Any]
    warnings: list[dict[str, str]]
    solver_statistics: dict[str, Any]


def _prepare_inputs(
    demands: pd.DataFrame,
    rooms: pd.DataFrame,
    historical_placements: pd.DataFrame,
    config: ScenarioConfig,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, set[str]]]:
    ready = demands.loc[
        demands["demand_input_status"].eq("ready_provisional_ladok_demand")
    ].copy()
    room_rows = rooms.loc[
        rooms["room_id"].isin(config.allowed_room_ids)
        & rooms["eligible_for_exploratory_capacity_poc"].astype(str).str.lower().eq("true")
    ].copy()
    missing_rooms = set(config.allowed_room_ids) - set(room_rows["room_id"])
    if missing_rooms:
        raise ValueError(
            "Konfigurationen refererar till rum som saknas eller inte är PoC-valbara: "
            + ", ".join(sorted(missing_rooms))
        )
    room_records: dict[str, dict[str, Any]] = {}
    for row in room_rows.to_dict(orient="records"):
        row["capacity_seats"] = int(row["capacity_seats"])
        room_records[str(row["room_id"])] = row
    historical_rooms = (
        historical_placements.dropna(subset=["room_id"])
        .groupby("demand_id")["room_id"]
        .agg(lambda values: {str(value) for value in values})
        .to_dict()
    )
    demand_records: list[dict[str, Any]] = []
    for row in ready.to_dict(orient="records"):
        raw_demand = float(row["demand_value"])
        if not raw_demand.is_integer():
            raise ValueError(f"Efterfrågan är inte ett heltal för {row['demand_id']}.")
        required = math.ceil(raw_demand * (1 + config.capacity_safety_margin_ratio))
        city_text = str(row.get("observed_cities") or "")
        cities = {part.strip() for part in city_text.split("|") if part.strip()}
        demand_records.append(
            {
                **row,
                "raw_demand": int(raw_demand),
                "required_demand": required,
                "historical_cities": cities,
                "options": options_for_demand(pd.Series(row), config),
            }
        )
    return demand_records, room_records, historical_rooms


def _solve_capacity_partition(
    demands: pd.DataFrame,
    rooms: pd.DataFrame,
    historical_placements: pd.DataFrame,
    config: ScenarioConfig,
) -> OptimizationResult:
    demand_records, room_records, historical_rooms = _prepare_inputs(
        demands, rooms, historical_placements, config
    )
    capacity_check = historical_capacity_check(
        demand_records, room_records, config.enforce_historical_city
    )
    model = cp_model.CpModel()
    selected: dict[tuple[int, int], cp_model.IntVar] = {}
    unplaced: dict[int, cp_model.IntVar] = {}
    use: dict[tuple[int, int, str], cp_model.IntVar] = {}
    seats: dict[tuple[int, int, str], cp_model.IntVar] = {}
    option_lookup: dict[tuple[int, int], dict[str, Any]] = {}

    for demand_index, demand in enumerate(demand_records):
        unplaced[demand_index] = model.NewBoolVar(f"unplaced_{demand_index}")
        if not config.allow_unplaced:
            model.Add(unplaced[demand_index] == 0)
        option_vars: list[cp_model.IntVar] = []
        for option_index, option in enumerate(demand["options"]):
            select_var = model.NewBoolVar(f"select_{demand_index}_{option_index}")
            selected[demand_index, option_index] = select_var
            option_lookup[demand_index, option_index] = option
            option_vars.append(select_var)
            allocation_vars: list[cp_model.IntVar] = []
            use_vars: list[cp_model.IntVar] = []
            for room_id, room in room_records.items():
                if config.enforce_historical_city and demand["historical_cities"]:
                    if str(room["reference_city"]) not in demand["historical_cities"]:
                        continue
                use_var = model.NewBoolVar(f"use_{demand_index}_{option_index}_{room_id}")
                seat_var = model.NewIntVar(
                    0,
                    min(demand["required_demand"], room["capacity_seats"]),
                    f"seats_{demand_index}_{option_index}_{room_id}",
                )
                use[demand_index, option_index, room_id] = use_var
                seats[demand_index, option_index, room_id] = seat_var
                model.Add(seat_var >= use_var)
                model.Add(seat_var <= demand["required_demand"] * use_var)
                model.Add(use_var <= select_var)
                allocation_vars.append(seat_var)
                use_vars.append(use_var)
            model.Add(sum(allocation_vars) == demand["required_demand"] * select_var)
            room_limit = config.max_rooms_per_exam if config.allow_split else 1
            model.Add(sum(use_vars) <= room_limit * select_var)
        model.Add(sum(option_vars) + unplaced[demand_index] == 1)

    active_segments: dict[tuple[str, str, int, int], cp_model.IntVar] = {}
    segment_loads: dict[tuple[str, str, int, int], cp_model.LinearExpr] = {}
    option_keys_by_date: dict[str, list[tuple[int, int]]] = {}
    boundaries_by_date: dict[str, set[int]] = {}
    for option_key, option in option_lookup.items():
        option_keys_by_date.setdefault(option["date"], []).append(option_key)
        boundaries_by_date.setdefault(option["date"], set()).update(
            (option["start"], option["occupancy_end"])
        )
    for day, boundaries in boundaries_by_date.items():
        ordered = sorted(boundaries)
        for segment_start, segment_end in zip(ordered, ordered[1:]):
            overlapping = [
                key
                for key in option_keys_by_date[day]
                if option_lookup[key]["start"] < segment_end
                and option_lookup[key]["occupancy_end"] > segment_start
            ]
            if not overlapping:
                continue
            for room_id, room in room_records.items():
                use_vars = [use[key[0], key[1], room_id] for key in overlapping if (*key, room_id) in use]
                if not use_vars:
                    continue
                seat_vars = [
                    seats[key[0], key[1], room_id]
                    for key in overlapping
                    if (*key, room_id) in seats
                ]
                active = model.NewBoolVar(
                    f"active_{room_id}_{day}_{segment_start}_{segment_end}"
                )
                active_segments[room_id, day, segment_start, segment_end] = active
                load = sum(seat_vars)
                segment_loads[room_id, day, segment_start, segment_end] = load
                model.Add(load <= room["capacity_seats"] * active)
                model.Add(active <= sum(use_vars))
                if not config.allow_co_location:
                    model.Add(sum(use_vars) <= 1)

    room_ever_used: dict[str, cp_model.IntVar] = {}
    for room_id in room_records:
        room_uses = [variable for key, variable in use.items() if key[2] == room_id]
        ever = model.NewBoolVar(f"room_ever_{room_id}")
        room_ever_used[room_id] = ever
        for variable in room_uses:
            model.Add(variable <= ever)
        model.Add(ever <= sum(room_uses))

    hint = historical_greedy_hint(demand_records, room_records, config)
    for demand_index, variable in unplaced.items():
        model.AddHint(variable, int(demand_index in hint["unplaced"]))
    for key, variable in selected.items():
        model.AddHint(variable, int(hint["selected_options"].get(key[0]) == key[1]))
    for key, variable in use.items():
        allocated = hint["allocations"].get(key, 0)
        model.AddHint(variable, int(allocated > 0))
        model.AddHint(seats[key], allocated)
    hinted_allocations = {
        key for key, allocated in hint["allocations"].items() if allocated > 0
    }
    for (room_id, day, segment_start, segment_end), variable in active_segments.items():
        is_active = any(
            allocation_room == room_id
            and option_lookup[demand_index, option_index]["date"] == day
            and option_lookup[demand_index, option_index]["start"] < segment_end
            and option_lookup[demand_index, option_index]["occupancy_end"] > segment_start
            for demand_index, option_index, allocation_room in hinted_allocations
        )
        model.AddHint(variable, int(is_active))
    for room_id, variable in room_ever_used.items():
        model.AddHint(
            variable,
            int(any(allocation_room == room_id for _, _, allocation_room in hinted_allocations)),
        )

    component_expressions: dict[str, cp_model.LinearExpr] = {
        "unplaced_participants": sum(
            demand["required_demand"] * unplaced[index]
            for index, demand in enumerate(demand_records)
        ),
        "unplaced_exams": sum(unplaced.values()),
        "distinct_rooms": sum(room_ever_used.values()),
        "room_open_minutes": sum(
            (segment_end - segment_start) * variable
            for (_, _, segment_start, segment_end), variable in active_segments.items()
        ),
        "unused_seat_minutes": sum(
            (segment_end - segment_start)
            * (room_records[room_id]["capacity_seats"] * active_segments[key] - segment_loads[key])
            for key in active_segments
            for room_id, _, segment_start, segment_end in [key]
        ),
        "rescheduled_exams": sum(
            variable
            for key, variable in selected.items()
            if not option_lookup[key]["is_historical_time"]
        ),
        "room_reassignments": sum(
            variable
            for (demand_index, _, room_id), variable in use.items()
            if room_id not in historical_rooms.get(demand_records[demand_index]["demand_id"], set())
        ),
    }
    objective = sum(
        config.objective_weights[name] * expression
        for name, expression in component_expressions.items()
    )
    model.Minimize(objective)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.max_time_seconds
    solver.parameters.num_search_workers = config.num_workers
    solver.parameters.random_seed = config.random_seed
    solver.parameters.relative_gap_limit = config.relative_gap_limit
    started = perf_counter()
    status_code = solver.Solve(model)
    runtime = perf_counter() - started
    status_name = solver.StatusName(status_code).lower()
    has_solution = status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    assignment_rows: list[dict[str, Any]] = []
    unplaced_rows: list[dict[str, Any]] = []
    if has_solution:
        for demand_index, demand in enumerate(demand_records):
            if solver.Value(unplaced[demand_index]):
                unplaced_rows.append(
                    {
                        "demand_id": demand["demand_id"],
                        "course_code": demand["course_code"],
                        "participants": demand["raw_demand"],
                        "required_seats": demand["required_demand"],
                        "reason": "selected_unplaced_by_optimization",
                    }
                )
                continue
            selected_key = next(
                key
                for key, variable in selected.items()
                if key[0] == demand_index and solver.Value(variable)
            )
            option = option_lookup[selected_key]
            for (item_index, option_index, room_id), variable in seats.items():
                if (item_index, option_index) != selected_key:
                    continue
                allocated = solver.Value(variable)
                if allocated <= 0:
                    continue
                assignment_rows.append(
                    {
                        "demand_id": demand["demand_id"],
                        "course_code": demand["course_code"],
                        "scheduled_date": option["date"],
                        "start_time": clock_text(option["start"]),
                        "end_time": clock_text(option["end"]),
                        "room_id": room_id,
                        "allocated_participants": allocated,
                        "required_seats_total": demand["required_demand"],
                        "original_date": demand["scheduled_date"],
                        "original_start_time": demand["booking_start_time"],
                        "date_shift_days": option["day_shift"],
                        "start_shift_minutes": option["minute_shift"],
                        "historical_room": room_id
                        in historical_rooms.get(demand["demand_id"], set()),
                    }
                )
    else:
        for demand in demand_records:
            unplaced_rows.append(
                {
                    "demand_id": demand["demand_id"],
                    "course_code": demand["course_code"],
                    "participants": demand["raw_demand"],
                    "required_seats": demand["required_demand"],
                    "reason": f"solver_{status_name}_without_solution",
                }
            )

    assignments = pd.DataFrame.from_records(assignment_rows)
    unplaced_frame = pd.DataFrame.from_records(unplaced_rows)
    component_values = {
        name: int(solver.Value(expression)) if has_solution else None
        for name, expression in component_expressions.items()
    }
    objective_value = float(solver.ObjectiveValue()) if has_solution else None
    best_bound = float(solver.BestObjectiveBound()) if status_code != cp_model.MODEL_INVALID else None
    gap = None
    if objective_value is not None and best_bound is not None:
        gap = abs(objective_value - best_bound) / max(1.0, abs(objective_value))
    peak_capacity = 0
    if has_solution:
        capacity_by_segment: dict[tuple[str, int, int], int] = {}
        for (room_id, day, start, end), variable in active_segments.items():
            if solver.Value(variable):
                key = (day, start, end)
                capacity_by_segment[key] = capacity_by_segment.get(key, 0) + room_records[room_id][
                    "capacity_seats"
                ]
        peak_capacity = max(capacity_by_segment.values(), default=0)
    metrics = {
        "input_exam_count": len(demand_records),
        "input_participants": sum(item["raw_demand"] for item in demand_records),
        "required_seats_with_margin": sum(item["required_demand"] for item in demand_records),
        "placed_exam_count": len(demand_records) - len(unplaced_rows) if has_solution else 0,
        "unplaced_exam_count": len(unplaced_rows),
        "unplaced_participants": int(unplaced_frame.get("participants", pd.Series(dtype=int)).sum()),
        "assignment_row_count": len(assignments),
        "rooms_used": int(assignments.get("room_id", pd.Series(dtype=str)).nunique()),
        "max_simultaneous_open_capacity": peak_capacity,
        "objective_components": component_values,
        **capacity_check,
    }
    if has_solution and unplaced_frame.empty:
        metrics["full_placement_feasibility"] = "demonstrated_feasible"
    elif (
        config.date_shift_earlier_days == 0
        and config.date_shift_later_days == 0
        and config.start_time_shift_minutes == 0
        and capacity_check["maximum_aggregate_capacity_shortfall"] > 0
    ):
        metrics["full_placement_feasibility"] = (
            "proven_impossible_by_aggregate_capacity_at_fixed_times"
        )
    else:
        metrics["full_placement_feasibility"] = "not_determined"
    warnings = [
        {
            "code": "SCENARIO_ROOM_AVAILABILITY_ASSUMED",
            "message": "Scenariorummen saknar verifierad kalendertillgänglighet.",
        },
        {
            "code": "SPECIAL_SUPPORT_NOT_MODELED",
            "message": "Särskilt stöd ingår inte som kompatibilitetskrav i denna PoC-körning.",
        },
        {
            "code": "DIGITAL_COMPATIBILITY_NOT_MODELED",
            "message": "Tentamensformat ingår inte som kompatibilitetskrav i denna PoC-körning.",
        },
        {
            "code": "PROVISIONAL_DEMAND_AND_CAPACITY",
            "message": "Efterfrågan och kapacitet är provisoriska analysvärden.",
        },
    ]
    sorted_assignments = (
        assignments.sort_values(["scheduled_date", "start_time", "room_id", "demand_id"])
        .reset_index(drop=True)
        if not assignments.empty
        else assignments
    )
    sorted_unplaced = (
        unplaced_frame.sort_values("demand_id").reset_index(drop=True)
        if not unplaced_frame.empty
        else unplaced_frame
    )
    return OptimizationResult(
        solver_status=status_name,
        solver_status_code=int(status_code),
        runtime_seconds=runtime,
        objective_value=objective_value,
        best_objective_bound=best_bound,
        relative_gap=gap,
        assignments=sorted_assignments,
        unplaced=sorted_unplaced,
        metrics=metrics,
        warnings=warnings,
        solver_statistics={
            "conflicts": solver.NumConflicts(),
            "branches": solver.NumBranches(),
            "wall_time_seconds": solver.WallTime(),
            "response_stats": solver.ResponseStats(),
        },
    )


def solve_capacity_scenario(
    demands: pd.DataFrame,
    rooms: pd.DataFrame,
    historical_placements: pd.DataFrame,
    config: ScenarioConfig,
) -> OptimizationResult:
    """Solve independent dates separately when the scenario never moves between dates."""
    ready = demands.loc[
        demands["demand_input_status"].eq("ready_provisional_ladok_demand")
    ].copy()
    if config.date_shift_earlier_days or config.date_shift_later_days or ready.empty:
        return _solve_capacity_partition(demands, rooms, historical_placements, config)
    groups = list(ready.groupby("scheduled_date", sort=True))
    total_rows = len(ready)
    results: list[tuple[str, OptimizationResult]] = []
    partition_diagnostics: list[dict[str, Any]] = []
    phase_count = 2 if config.start_time_shift_minutes > 0 else 1
    for day, frame in groups:
        budget = max(
            0.1,
            config.max_time_seconds * len(frame) / total_rows / phase_count,
        )
        partition_config = replace(config, max_time_seconds=budget)
        demand_ids = set(frame["demand_id"])
        partition_placements = historical_placements.loc[
            historical_placements["demand_id"].isin(demand_ids)
        ]
        flexible_result = _solve_capacity_partition(
            frame, rooms, partition_placements, partition_config
        )
        candidates = [("configured", flexible_result)]
        if config.start_time_shift_minutes > 0:
            fixed_config = replace(partition_config, start_time_shift_minutes=0)
            fixed_result = _solve_capacity_partition(
                frame, rooms, partition_placements, fixed_config
            )
            candidates.append(("fixed_time_fallback", fixed_result))
        feasible_candidates = [
            item for item in candidates if item[1].objective_value is not None
        ]
        selected_source, selected_result = min(
            feasible_candidates or candidates,
            key=lambda item: (
                item[1].objective_value
                if item[1].objective_value is not None
                else float("inf")
            ),
        )
        results.append((str(day), selected_result))
        partition_diagnostics.append(
            {
                "scheduled_date": str(day),
                "selected_source": selected_source,
                "candidates": [
                    {
                        "source": source,
                        "status": result.solver_status,
                        "objective_value": result.objective_value,
                        "runtime_seconds": result.runtime_seconds,
                    }
                    for source, result in candidates
                ],
            }
        )
    assignments = pd.concat(
        [result.assignments for _, result in results], ignore_index=True
    )
    unplaced = pd.concat([result.unplaced for _, result in results], ignore_index=True)
    component_names = next(
        iter(result.metrics["objective_components"] for _, result in results)
    ).keys()
    components = {
        name: sum(
            result.metrics["objective_components"][name] or 0 for _, result in results
        )
        for name in component_names
    }
    components["distinct_rooms"] = int(
        assignments.get("room_id", pd.Series(dtype=str)).nunique()
    )
    objective_value = float(
        sum(config.objective_weights[name] * value for name, value in components.items())
    )
    invalid = any(
        result.solver_status in {"model_invalid", "infeasible"} for _, result in results
    )
    status = "model_invalid" if invalid else "feasible"
    metrics = {
        "input_exam_count": sum(result.metrics["input_exam_count"] for _, result in results),
        "input_participants": sum(
            result.metrics["input_participants"] for _, result in results
        ),
        "required_seats_with_margin": sum(
            result.metrics["required_seats_with_margin"] for _, result in results
        ),
        "placed_exam_count": sum(
            result.metrics["placed_exam_count"] for _, result in results
        ),
        "unplaced_exam_count": len(unplaced),
        "unplaced_participants": int(
            unplaced.get("participants", pd.Series(dtype=int)).sum()
        ),
        "assignment_row_count": len(assignments),
        "rooms_used": components["distinct_rooms"],
        "max_simultaneous_open_capacity": max(
            result.metrics["max_simultaneous_open_capacity"] for _, result in results
        ),
        "objective_components": components,
        "input_peak_concurrent_required_seats": max(
            result.metrics["input_peak_concurrent_required_seats"] for _, result in results
        ),
        "maximum_aggregate_capacity_shortfall": max(
            result.metrics["maximum_aggregate_capacity_shortfall"] for _, result in results
        ),
    }
    peak_result = max(
        (result for _, result in results),
        key=lambda item: item.metrics["input_peak_concurrent_required_seats"],
    )
    metrics["input_peak_context"] = peak_result.metrics["input_peak_context"]
    if metrics["unplaced_exam_count"] == 0:
        metrics["full_placement_feasibility"] = "demonstrated_feasible"
    elif config.start_time_shift_minutes == 0 and all(
        result.metrics["full_placement_feasibility"]
        == "proven_impossible_by_aggregate_capacity_at_fixed_times"
        or result.metrics["maximum_aggregate_capacity_shortfall"] == 0
        for _, result in results
    ) and metrics["maximum_aggregate_capacity_shortfall"] > 0:
        metrics["full_placement_feasibility"] = (
            "proven_impossible_by_aggregate_capacity_at_fixed_times"
        )
    else:
        metrics["full_placement_feasibility"] = "not_determined"
    warnings = list(results[0][1].warnings)
    warnings.append(
        {
            "code": "INDEPENDENT_DATE_DECOMPOSITION",
            "message": (
                "Datum utan tillåten datumförflyttning löstes som oberoende delproblem. "
                "Resultatet är reproducerbart men global optimalitet för det viktade målet hävdas inte."
            ),
        }
    )
    sorted_assignments = (
        assignments.sort_values(["scheduled_date", "start_time", "room_id", "demand_id"])
        .reset_index(drop=True)
        if not assignments.empty
        else assignments
    )
    sorted_unplaced = (
        unplaced.sort_values("demand_id").reset_index(drop=True)
        if not unplaced.empty
        else unplaced
    )
    return OptimizationResult(
        solver_status=status,
        solver_status_code=int(cp_model.MODEL_INVALID if invalid else cp_model.FEASIBLE),
        runtime_seconds=sum(
            candidate["runtime_seconds"]
            for item in partition_diagnostics
            for candidate in item["candidates"]
        ),
        objective_value=objective_value if not invalid else None,
        best_objective_bound=None,
        relative_gap=None,
        assignments=sorted_assignments,
        unplaced=sorted_unplaced,
        metrics=metrics,
        warnings=warnings,
        solver_statistics={
            "strategy": "independent_date_decomposition",
            "partition_count": len(results),
            "partition_statuses": partition_diagnostics,
            "conflicts": sum(result.solver_statistics["conflicts"] for _, result in results),
            "branches": sum(result.solver_statistics["branches"] for _, result in results),
            "wall_time_seconds": sum(
                result.solver_statistics["wall_time_seconds"] for _, result in results
            ),
        },
    )
