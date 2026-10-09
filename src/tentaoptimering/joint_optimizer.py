"""CP-SAT optimizer coupling calendar, real rooms and staffing cost."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any

from ortools.sat.python import cp_model

from .joint_contract import (
    RESULT_SCHEMA_VERSION,
    CostBreakdown,
    CoverageSummary,
    ExamDemand,
    JointOptimizationInput,
    JointOptimizationResult,
    SolverSummary,
    validate_problem,
)


@dataclass
class _Variables:
    selected: dict[tuple[str, str], cp_model.IntVar]
    seats: dict[tuple[str, str, str], cp_model.IntVar]
    uses: dict[tuple[str, str, str], cp_model.IntVar]
    sessions: dict[tuple[str, str], cp_model.IntVar]
    occupancy: dict[tuple[str, str], cp_model.IntVar]
    staff: dict[tuple[str, str], cp_model.IntVar]
    session_end: dict[tuple[str, str], cp_model.IntVar]
    owned: dict[str, cp_model.IntVar]
    staff_pool: cp_model.IntVar


def solve_joint_optimization(problem: JointOptimizationInput) -> JointOptimizationResult:
    """Solve the complete modeled demand; partial placement is never an objective option."""
    validate_problem(problem)
    blocked = tuple(item.exam_demand_id for item in problem.demands if not item.candidate_slot_ids)
    if blocked:
        return _blocked_result(problem, blocked)
    model = cp_model.CpModel()
    slots = {slot.slot_id: slot for slot in problem.slots}
    variables = _build_variables_and_constraints(model, problem, slots)
    room_cost = sum(
        room.annual_fixed_cost_ore * variables.owned[room.room_id]
        for room in problem.rooms
    )
    external_cost = sum(
        room.external_session_cost_ore * variables.sessions[room.room_id, slot.slot_id]
        for room in problem.rooms
        for slot in problem.slots
    )
    staff_pool_cost = problem.staffing.annual_cost_ore_per_staff * variables.staff_pool
    staff_session_cost = problem.staffing.cost_ore_per_staff_session * sum(variables.staff.values())
    total_cost = room_cost + external_cost + staff_pool_cost + staff_session_cost
    changed_terms = _change_terms(problem, variables.selected)
    model.Minimize(total_cost)

    started = time.perf_counter()
    solver = _solver(problem)
    status = solver.Solve(model)
    phase_one_seconds = time.perf_counter() - started
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _empty_result(problem, solver, status, phase_one_seconds)

    economic_solver = solver
    economic_status = status
    change_status = "not_run_economic_optimum_not_proven"
    if status == cp_model.OPTIMAL and changed_terms:
        remaining = problem.solver.time_limit_seconds - phase_one_seconds
        if remaining > 0.01:
            optimum = int(round(solver.ObjectiveValue()))
            model.Add(total_cost == optimum)
            model.Minimize(sum(changed_terms))
            preference_solver = _solver(problem, remaining)
            preference_status = preference_solver.Solve(model)
            if preference_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solver = preference_solver
                change_status = (
                    "optimal_at_economic_optimum"
                    if preference_status == cp_model.OPTIMAL
                    else "feasible_at_economic_optimum"
                )
            else:
                change_status = "not_run_time_limit_after_economic_optimum"
        else:
            change_status = "not_run_time_limit_after_economic_optimum"
    elif status == cp_model.OPTIMAL:
        change_status = "not_applicable_no_historical_slots"

    elapsed = time.perf_counter() - started
    cost_value = int(economic_solver.ObjectiveValue())
    bound = math.ceil(economic_solver.BestObjectiveBound() - 1e-7)
    gap = max(0.0, (cost_value - bound) / max(1, abs(cost_value)))
    assignments, sessions, schedule = _extract(problem, solver, variables, slots)
    physical_assigned = sum(row["participants"] for row in assignments)
    non_room = sum(demand.participant_count for demand in problem.demands if not demand.requires_room)
    demand_by_id = {item.exam_demand_id: item for item in problem.demands}
    changed = sum(
        1
        for row in schedule
        if _is_changed(demand_by_id[row["exam_demand_id"]], row["slot_id"], slots)
    )
    costs = CostBreakdown(
        annual_room_cost_ore=int(solver.Value(room_cost)),
        external_room_session_cost_ore=int(solver.Value(external_cost)),
        annual_staff_pool_cost_ore=int(solver.Value(staff_pool_cost)),
        staff_session_cost_ore=int(solver.Value(staff_session_cost)),
        comparable_total_cost_ore=int(solver.Value(total_cost)),
    )
    return JointOptimizationResult(
        schema_version=RESULT_SCHEMA_VERSION,
        problem_id=problem.problem_id,
        solver=SolverSummary(
            outcome="optimal" if economic_status == cp_model.OPTIMAL else "feasible_not_proven",
            raw_status=economic_solver.StatusName(economic_status).lower(),
            objective_value_ore=cost_value,
            best_objective_bound_ore=bound,
            relative_gap=gap,
            wall_time_seconds=elapsed,
            change_preference_status=change_status,
        ),
        costs=costs,
        coverage=CoverageSummary(
            exam_demands_total=len(problem.demands),
            exam_demands_scheduled=len(schedule),
            participants_total=sum(item.participant_count for item in problem.demands),
            participants_assigned_to_rooms=physical_assigned,
            non_room_participants_scheduled=non_room,
            technical_placement_complete=len(schedule) == len(problem.demands)
            and physical_assigned + non_room == sum(item.participant_count for item in problem.demands),
        ),
        staff_pool_size=int(solver.Value(variables.staff_pool)),
        changed_exam_demands=changed,
        assignments=assignments,
        room_sessions=sessions,
        schedule=schedule,
        limitations=_limitations(problem),
        verification=_verification(problem, economic_status == cp_model.OPTIMAL, assignments),
    )


def _build_variables_and_constraints(
    model: cp_model.CpModel,
    problem: JointOptimizationInput,
    slots: dict[str, Any],
) -> _Variables:
    selected: dict[tuple[str, str], cp_model.IntVar] = {}
    seats: dict[tuple[str, str, str], cp_model.IntVar] = {}
    uses: dict[tuple[str, str, str], cp_model.IntVar] = {}
    sessions: dict[tuple[str, str], cp_model.IntVar] = {}
    occupancy: dict[tuple[str, str], cp_model.IntVar] = {}
    staff: dict[tuple[str, str], cp_model.IntVar] = {}
    session_end: dict[tuple[str, str], cp_model.IntVar] = {}
    owned = {
        room.room_id: model.NewBoolVar(f"owned_{room.room_id}") for room in problem.rooms
    }
    max_staff = problem.staffing.ladder[-1].required_staff
    max_ladder_capacity = problem.staffing.ladder[-1].max_participants
    for room in problem.rooms:
        for slot in problem.slots:
            key = room.room_id, slot.slot_id
            sessions[key] = model.NewBoolVar(f"session_{room.room_id}_{slot.slot_id}")
            occupancy[key] = model.NewIntVar(0, room.capacity, f"occupancy_{room.room_id}_{slot.slot_id}")
            staff[key] = model.NewIntVar(0, max_staff, f"staff_{room.room_id}_{slot.slot_id}")
            session_end[key] = model.NewIntVar(
                slot.start_minute, slot.latest_end_minute, f"end_{room.room_id}_{slot.slot_id}"
            )

    for demand in problem.demands:
        choices = []
        for slot_id in demand.candidate_slot_ids:
            choice = model.NewBoolVar(f"selected_{demand.exam_demand_id}_{slot_id}")
            selected[demand.exam_demand_id, slot_id] = choice
            choices.append(choice)
            if not demand.requires_room:
                continue
            allocations = []
            room_uses = []
            for room in problem.rooms:
                if not _compatible(demand, room, slot_id):
                    continue
                key = demand.exam_demand_id, slot_id, room.room_id
                use = model.NewBoolVar(f"use_{demand.exam_demand_id}_{slot_id}_{room.room_id}")
                seat = model.NewIntVar(
                    0,
                    min(demand.participant_count, room.capacity, max_ladder_capacity),
                    f"seats_{demand.exam_demand_id}_{slot_id}_{room.room_id}",
                )
                uses[key] = use
                seats[key] = seat
                model.Add(seat >= use)
                model.Add(seat <= room.capacity * use)
                model.Add(use <= choice)
                model.Add(use <= sessions[room.room_id, slot_id])
                model.Add(session_end[room.room_id, slot_id] >= slots[slot_id].start_minute + demand.duration_minutes).OnlyEnforceIf(use)
                allocations.append(seat)
                room_uses.append((room, use))
            model.Add(sum(allocations) == demand.participant_count * choice)
            model.Add(sum(use for _, use in room_uses) <= demand.max_rooms * choice)
            if not demand.allow_split_across_buildings:
                for index, (left_room, left_use) in enumerate(room_uses):
                    for right_room, right_use in room_uses[index + 1 :]:
                        if left_room.building_id != right_room.building_id:
                            model.Add(left_use + right_use <= 1)
        model.Add(sum(choices) == 1)

    for room in problem.rooms:
        room_sessions = []
        lookup = _staff_lookup(room.capacity, problem)
        duration_by_demand = {
            demand.exam_demand_id: demand.duration_minutes for demand in problem.demands
        }
        for slot in problem.slots:
            room_key = room.room_id, slot.slot_id
            relevant = [
                key for key in seats if key[1] == slot.slot_id and key[2] == room.room_id
            ]
            model.Add(occupancy[room_key] == sum(seats[key] for key in relevant))
            model.Add(occupancy[room_key] >= sessions[room_key])
            model.Add(occupancy[room_key] <= room.capacity * sessions[room_key])
            model.Add(occupancy[room_key] <= max_ladder_capacity)
            model.AddElement(occupancy[room_key], lookup, staff[room_key])
            model.Add(sessions[room_key] <= owned[room.room_id])
            model.AddMaxEquality(
                session_end[room_key],
                [slot.start_minute]
                + [
                    slot.start_minute + duration_by_demand[key[0]] * uses[key]
                    for key in relevant
                ],
            )
            room_sessions.append(sessions[room_key])
        model.Add(owned[room.room_id] <= sum(room_sessions))
        _room_non_overlap(model, room.room_id, problem, sessions, session_end)

    _demand_conflicts(model, problem, selected, slots)
    pool_upper = len(problem.rooms) * max_staff
    staff_pool = model.NewIntVar(0, pool_upper, "staff_pool")
    for current in problem.slots:
        checkpoint = current.start_minute - problem.staffing.preparation_minutes
        possible = [
            slot for slot in problem.slots
            if slot.scheduled_date == current.scheduled_date
            and slot.start_minute - problem.staffing.preparation_minutes <= checkpoint
            and slot.latest_end_minute + problem.staffing.closing_minutes > checkpoint
        ]
        active_staff = []
        for room in problem.rooms:
            for slot in possible:
                key = room.room_id, slot.slot_id
                end_after = model.NewBoolVar(f"end_after_{room.room_id}_{slot.slot_id}_{current.slot_id}")
                active = model.NewBoolVar(f"active_{room.room_id}_{slot.slot_id}_{current.slot_id}")
                count = model.NewIntVar(0, max_staff, f"active_staff_{room.room_id}_{slot.slot_id}_{current.slot_id}")
                model.Add(session_end[key] + problem.staffing.closing_minutes >= checkpoint + 1).OnlyEnforceIf(end_after)
                model.Add(session_end[key] + problem.staffing.closing_minutes <= checkpoint).OnlyEnforceIf(end_after.Not())
                model.Add(active <= sessions[key])
                model.Add(active <= end_after)
                model.Add(active >= sessions[key] + end_after - 1)
                model.Add(count <= staff[key])
                model.Add(count <= max_staff * active)
                model.Add(count >= staff[key] - max_staff * (1 - active))
                active_staff.append(count)
        model.Add(sum(active_staff) <= staff_pool)
    return _Variables(
        selected, seats, uses, sessions, occupancy, staff, session_end, owned, staff_pool
    )


def _room_non_overlap(
    model: cp_model.CpModel,
    room_id: str,
    problem: JointOptimizationInput,
    sessions: dict[tuple[str, str], cp_model.IntVar],
    ends: dict[tuple[str, str], cp_model.IntVar],
) -> None:
    ordered = sorted(problem.slots, key=lambda item: (item.scheduled_date, item.start_minute))
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if left.scheduled_date != right.scheduled_date:
                break
            model.Add(ends[room_id, left.slot_id] + problem.turnaround_minutes <= right.start_minute).OnlyEnforceIf(
                [sessions[room_id, left.slot_id], sessions[room_id, right.slot_id]]
            )


def _demand_conflicts(
    model: cp_model.CpModel,
    problem: JointOptimizationInput,
    selected: dict[tuple[str, str], cp_model.IntVar],
    slots: dict[str, Any],
) -> None:
    for index, left in enumerate(problem.demands):
        for right in problem.demands[index + 1 :]:
            if not _conflicts(left, right):
                continue
            for left_id in left.candidate_slot_ids:
                for right_id in right.candidate_slot_ids:
                    if _overlap(slots[left_id], left.duration_minutes, slots[right_id], right.duration_minutes):
                        model.Add(selected[left.exam_demand_id, left_id] + selected[right.exam_demand_id, right_id] <= 1)


def _compatible(demand: ExamDemand, room: Any, slot_id: str) -> bool:
    return (
        room.plan_area == demand.plan_area
        and (room.available_slot_ids is None or slot_id in room.available_slot_ids)
        and (
            demand.digital_requirement in {"none", "unknown"}
            or demand.digital_requirement in room.digital_capabilities
        )
    )


def _conflicts(left: ExamDemand, right: ExamDemand) -> bool:
    return bool(
        (left.course_code and left.course_code == right.course_code)
        or set(left.conflict_group_ids).intersection(right.conflict_group_ids)
    )


def _overlap(left: Any, left_duration: int, right: Any, right_duration: int) -> bool:
    return left.scheduled_date == right.scheduled_date and (
        left.start_minute < right.start_minute + right_duration
        and right.start_minute < left.start_minute + left_duration
    )


def _staff_lookup(capacity: int, problem: JointOptimizationInput) -> list[int]:
    lookup = [0]
    for participants in range(1, capacity + 1):
        matching = next(
            (step.required_staff for step in problem.staffing.ladder if participants <= step.max_participants),
            problem.staffing.ladder[-1].required_staff,
        )
        lookup.append(matching)
    return lookup


def _change_terms(problem: JointOptimizationInput, selected: dict[tuple[str, str], cp_model.IntVar]) -> list[Any]:
    """Only demands whose historical slot is an allowed candidate can avoid a change."""
    return [
        1 - selected[demand.exam_demand_id, demand.original_slot_id]
        for demand in problem.demands
        if demand.original_slot_id is not None and demand.original_slot_id in demand.candidate_slot_ids
    ]


def _is_changed(demand: ExamDemand, slot_id: str, slots: dict[str, Any]) -> bool:
    """A demand has changed when it is not at its historical date and start."""
    slot = slots[slot_id]
    if demand.original_date is not None and demand.original_start_minute is not None:
        return (slot.scheduled_date, slot.start_minute) != (demand.original_date, demand.original_start_minute)
    return demand.original_slot_id is not None and slot_id != demand.original_slot_id


def _extract(
    problem: JointOptimizationInput,
    solver: cp_model.CpSolver,
    variables: _Variables,
    slots: dict[str, Any],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    schedule = []
    assignments = []
    for demand in problem.demands:
        slot_id = next(
            slot_id for slot_id in demand.candidate_slot_ids
            if solver.Value(variables.selected[demand.exam_demand_id, slot_id])
        )
        schedule.append({
            "exam_demand_id": demand.exam_demand_id,
            "slot_id": slot_id,
            "original_slot_id": demand.original_slot_id,
            "original_date": demand.original_date.isoformat() if demand.original_date else None,
            "original_start_minute": demand.original_start_minute,
            "requires_room": demand.requires_room,
            "participants": demand.participant_count,
        })
        for room in problem.rooms:
            key = demand.exam_demand_id, slot_id, room.room_id
            if key in variables.seats and solver.Value(variables.seats[key]):
                assignments.append({
                    "exam_demand_id": demand.exam_demand_id,
                    "slot_id": slot_id,
                    "room_id": room.room_id,
                    "participants": int(solver.Value(variables.seats[key])),
                })
    room_sessions = []
    for room in problem.rooms:
        for slot in problem.slots:
            key = room.room_id, slot.slot_id
            if not solver.Value(variables.sessions[key]):
                continue
            members = sorted({
                row["exam_demand_id"] for row in assignments
                if row["room_id"] == room.room_id and row["slot_id"] == slot.slot_id
            })
            actual_end = max(
                slot.start_minute + next(item.duration_minutes for item in problem.demands if item.exam_demand_id == demand_id)
                for demand_id in members
            )
            room_sessions.append({
                "room_id": room.room_id,
                "building_id": room.building_id,
                "slot_id": slot.slot_id,
                "exam_demand_ids": members,
                "participants": int(solver.Value(variables.occupancy[key])),
                "required_staff": int(solver.Value(variables.staff[key])),
                "available_again_minute": actual_end + problem.turnaround_minutes,
            })
    order = lambda row: tuple(str(row[name]) for name in sorted(row))
    return tuple(sorted(assignments, key=order)), tuple(sorted(room_sessions, key=order)), tuple(sorted(schedule, key=order))


def _solver(problem: JointOptimizationInput, time_limit: float | None = None) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit or problem.solver.time_limit_seconds
    solver.parameters.random_seed = problem.solver.random_seed
    solver.parameters.num_search_workers = problem.solver.num_workers
    return solver


def _empty_result(problem: JointOptimizationInput, solver: cp_model.CpSolver, status: int, elapsed: float) -> JointOptimizationResult:
    outcome = "infeasible" if status == cp_model.INFEASIBLE else "no_feasibility_conclusion"
    return JointOptimizationResult(
        RESULT_SCHEMA_VERSION,
        problem.problem_id,
        SolverSummary(outcome, solver.StatusName(status).lower(), None, None, None, elapsed, "not_run"),
        None,
        CoverageSummary(len(problem.demands), 0, sum(item.participant_count for item in problem.demands), 0, 0, False),
        None,
        None,
        (),
        (),
        (),
        _limitations(problem),
    )


def _blocked_result(problem: JointOptimizationInput, blocked: tuple[str, ...]) -> JointOptimizationResult:
    """Report impossible candidate generation as a blocking requirement, not as a crash."""
    shown = ", ".join(blocked[:10]) + (" …" if len(blocked) > 10 else "")
    return JointOptimizationResult(
        RESULT_SCHEMA_VERSION,
        problem.problem_id,
        SolverSummary("infeasible", "blocked_before_solve", None, None, None, 0.0, "not_run"),
        None,
        CoverageSummary(len(problem.demands), 0, sum(item.participant_count for item in problem.demands), 0, 0, False),
        None,
        None,
        (),
        (),
        (),
        (
            f"Blockerande krav: {len(blocked)} tentamensbehov saknar tillåtet tillfälle med nuvarande "
            f"fönster, veckodagar, starttider och spärrar: {shown}.",
            *_limitations(problem),
        ),
        {
            "solver": "infeasible_before_solve",
            "independent_validation": "not_performed",
            "blocking_demands": ",".join(blocked),
        },
    )


def _verification(
    problem: JointOptimizationInput, proven_optimal: bool, assignments: tuple[dict[str, Any], ...]
) -> dict[str, str]:
    """State what has and has not been verified; a solver status is not an independent check."""
    demands = {item.exam_demand_id: item for item in problem.demands}
    rooms = {item.room_id: item for item in problem.rooms}
    unquantified = {
        row["exam_demand_id"] for row in assignments
        if demands[row["exam_demand_id"]].digital_requirement == "e_exam"
        and rooms[row["room_id"]].digital_support_basis != "all_places"
    }
    unobserved = {
        item.exam_demand_id for item in problem.demands
        if item.digital_requirement == "e_exam" and item.digital_requirement_basis in {"unobserved", "observed_mixed"}
    }
    if unquantified or unobserved:
        digital = (
            f"assumed_not_verified: {len(unquantified)} digitala behov i salar med ej kvantifierat digitalstöd, "
            f"{len(unobserved)} behov med okänd eller blandad digital status"
        )
    else:
        digital = "consistent_with_published_room_support_not_verified_for_period"
    multi = sum(1 for item in problem.demands if item.participant_group_basis != "single_activity")
    return {
        "solver": "optimal_proven" if proven_optimal else "feasible_not_proven",
        "independent_validation": "not_performed",
        "digital_compatibility": digital,
        "group_disjointness": (
            f"assumed_not_verified: {multi} samtentor summerar deltagare från flera Ladokaktiviteter"
            if multi else "not_applicable"
        ),
        "student_overlap": "not_evaluated",
    }


def _limitations(problem: JointOptimizationInput) -> tuple[str, ...]:
    unsupported = sorted(
        item.parameter_id for item in problem.parameters if item.engine_support != "implemented"
    )
    result = [
        "Bemanningen optimeras som anonym samtidig pool per fast passfönster; individuell vaktplanering ingår inte.",
        "Kostnadsresultat följer kontraktets explicita antaganden och är inte verifierad realiserbar besparing.",
    ]
    if unsupported:
        result.append("Parametrar utan motorstöd: " + ", ".join(unsupported) + ".")
    ignored = sorted(
        item.parameter_id for item in problem.parameters
        if item.engine_support != "implemented" and item.changed_from_default
    )
    if ignored:
        result.append("Parametrar med ändrat värde men utan motorstöd (ignoreras): " + ", ".join(ignored) + ".")
    result.append("Resultatet är solververifierat men inte oberoende eftervaliderat.")
    if problem.scope.unresolved_source_activities:
        result.append(
            f"{problem.scope.unresolved_source_activities} källaktiviteter är oavgjorda utanför den modellerade omfattningen."
        )
    return tuple(result)
