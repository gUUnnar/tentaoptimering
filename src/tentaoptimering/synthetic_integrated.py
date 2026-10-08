"""A small integrated CP-SAT proof case for the target architecture.

The production solver is intentionally not replaced here.  This module proves the
essential coupling: room portfolio choices create room sessions, sessions create
staffing cost, and every included participant remains a hard demand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class SyntheticPass:
    pass_id: str
    start_minute: int
    duration_minutes: int
    turnaround_minutes: int


@dataclass(frozen=True)
class SyntheticExamDemand:
    exam_demand_id: str
    participant_count: int
    duration_minutes: int
    allowed_pass_ids: tuple[str, ...]


@dataclass(frozen=True)
class SyntheticRoom:
    room_id: str
    capacity: int
    annual_cost_ore: int
    staffing_cost_ore_per_session: int


@dataclass(frozen=True)
class SyntheticIntegratedResult:
    objective_ore: int
    annual_room_cost_ore: int
    staffing_cost_ore: int
    assignments: tuple[dict[str, Any], ...]
    room_sessions: tuple[dict[str, Any], ...]


def solve_synthetic_integrated(
    exams: tuple[SyntheticExamDemand, ...],
    passes: tuple[SyntheticPass, ...],
    rooms: tuple[SyntheticRoom, ...],
) -> SyntheticIntegratedResult:
    """Minimize annual room cost plus session-derived staffing cost.

    A room session has one common pass start, any number of participating exams and
    an availability time after the longest included exam plus turnaround.
    """
    _validate_inputs(exams, passes, rooms)
    model = cp_model.CpModel()
    pass_by_id = {item.pass_id: item for item in passes}
    starts: dict[tuple[str, str], cp_model.IntVar] = {}
    seats: dict[tuple[str, str, str], cp_model.IntVar] = {}
    uses: dict[tuple[str, str, str], cp_model.IntVar] = {}
    sessions: dict[tuple[str, str], cp_model.IntVar] = {}
    owned: dict[str, cp_model.IntVar] = {}
    for room in rooms:
        owned[room.room_id] = model.NewBoolVar(f"own_{room.room_id}")
        for exam_pass in passes:
            sessions[room.room_id, exam_pass.pass_id] = model.NewBoolVar(
                f"session_{room.room_id}_{exam_pass.pass_id}"
            )
    for exam in exams:
        choices: list[cp_model.IntVar] = []
        for pass_id in exam.allowed_pass_ids:
            start = model.NewBoolVar(f"start_{exam.exam_demand_id}_{pass_id}")
            starts[exam.exam_demand_id, pass_id] = start
            choices.append(start)
            allocations: list[cp_model.IntVar] = []
            for room in rooms:
                use = model.NewBoolVar(f"use_{exam.exam_demand_id}_{pass_id}_{room.room_id}")
                seat = model.NewIntVar(0, min(exam.participant_count, room.capacity), f"seats_{exam.exam_demand_id}_{pass_id}_{room.room_id}")
                uses[exam.exam_demand_id, pass_id, room.room_id] = use
                seats[exam.exam_demand_id, pass_id, room.room_id] = seat
                model.Add(seat >= use)
                model.Add(seat <= room.capacity * use)
                model.Add(use <= start)
                model.Add(use <= sessions[room.room_id, pass_id])
                allocations.append(seat)
            model.Add(sum(allocations) == exam.participant_count * start)
        model.Add(sum(choices) == 1)
    for room in rooms:
        room_sessions = [sessions[room.room_id, item.pass_id] for item in passes]
        model.Add(owned[room.room_id] <= sum(room_sessions))
        for left_index, left in enumerate(passes):
            for right in passes[left_index + 1 :]:
                left_end = left.start_minute + left.duration_minutes + left.turnaround_minutes
                right_end = right.start_minute + right.duration_minutes + right.turnaround_minutes
                if left.start_minute < right_end and right.start_minute < left_end:
                    model.Add(sessions[room.room_id, left.pass_id] + sessions[room.room_id, right.pass_id] <= 1)
        for item in passes:
            session = sessions[room.room_id, item.pass_id]
            room_uses = [
                uses[exam.exam_demand_id, item.pass_id, room.room_id]
                for exam in exams
                if item.pass_id in exam.allowed_pass_ids
            ]
            model.Add(sum(room_uses) <= len(room_uses) * session)
            model.Add(session <= sum(room_uses))
            model.Add(sum(seats[exam.exam_demand_id, item.pass_id, room.room_id] for exam in exams if item.pass_id in exam.allowed_pass_ids) <= room.capacity)
            model.Add(session <= owned[room.room_id])
    room_cost = sum(room.annual_cost_ore * owned[room.room_id] for room in rooms)
    staff_cost = sum(
        room.staffing_cost_ore_per_session * sessions[room.room_id, exam_pass.pass_id]
        for room in rooms
        for exam_pass in passes
    )
    model.Minimize(room_cost + staff_cost)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError(f"Det syntetiska testfallet saknar fullständig lösning: {solver.StatusName(status)}")
    assignments: list[dict[str, Any]] = []
    session_members: dict[tuple[str, str], list[SyntheticExamDemand]] = {}
    for exam in exams:
        for pass_id in exam.allowed_pass_ids:
            if not solver.Value(starts[exam.exam_demand_id, pass_id]):
                continue
            for room in rooms:
                count = solver.Value(seats[exam.exam_demand_id, pass_id, room.room_id])
                if count:
                    assignments.append({"exam_demand_id": exam.exam_demand_id, "pass_id": pass_id, "room_id": room.room_id, "participants": count})
                    session_members.setdefault((room.room_id, pass_id), []).append(exam)
    room_sessions: list[dict[str, Any]] = []
    for (room_id, pass_id), members in session_members.items():
        exam_pass = pass_by_id[pass_id]
        latest_end = exam_pass.start_minute + max(member.duration_minutes for member in members)
        room_sessions.append({"room_id": room_id, "pass_id": pass_id, "start_minute": exam_pass.start_minute, "exam_demand_ids": tuple(member.exam_demand_id for member in members), "available_again_minute": latest_end + exam_pass.turnaround_minutes})
    return SyntheticIntegratedResult(
        objective_ore=int(solver.ObjectiveValue()),
        annual_room_cost_ore=int(solver.Value(room_cost)),
        staffing_cost_ore=int(solver.Value(staff_cost)),
        assignments=tuple(sorted(assignments, key=lambda item: (item["room_id"], item["exam_demand_id"]))),
        room_sessions=tuple(sorted(room_sessions, key=lambda item: item["room_id"])),
    )


def _validate_inputs(exams: tuple[SyntheticExamDemand, ...], passes: tuple[SyntheticPass, ...], rooms: tuple[SyntheticRoom, ...]) -> None:
    if not exams or not passes or not rooms:
        raise ValueError("Det syntetiska fallet kräver tentamensbehov, pass och rum.")
    pass_ids = {item.pass_id for item in passes}
    if len(pass_ids) != len(passes) or len({item.room_id for item in rooms}) != len(rooms):
        raise ValueError("Pass- och rumsidentifierare måste vara unika.")
    if len({item.exam_demand_id for item in exams}) != len(exams):
        raise ValueError("exam_demand_id måste vara unikt.")
    for exam in exams:
        allowed = set(exam.allowed_pass_ids)
        if exam.participant_count <= 0 or exam.duration_minutes <= 0 or not allowed <= pass_ids:
            raise ValueError("Ett tentamensbehov har ogiltig kapacitet, varaktighet eller passmängd.")
        if any(exam.duration_minutes > item.duration_minutes for item in passes if item.pass_id in allowed):
            raise ValueError("Ett tentamensbehov är längre än ett tillåtet skrivpass.")
