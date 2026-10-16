"""Paid staff time in the CP-SAT model: every staff position of a room session is a paid pass (see `joint_costing`).

For each room and slot there is one product `staff * paid length` where the paid length is the longest exam of the session
plus preparation and closing, at least the shortest paid pass, plus the room's travel minutes; zero if the room has no
session at the slot. The cost is the paid minute price times the sum of these products. The same terms are built for the
monolithic model and for each day check of the decomposed strategy, so the cost means one thing in every path.
"""

from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

from .joint_contract import JointOptimizationInput


def paid_time_active(problem: JointOptimizationInput) -> bool:
    return problem.staffing.paid_minute_cost_ore > 0


def add_paid_time(model: cp_model.CpModel, problem: JointOptimizationInput, variables: Any) -> Any:
    """The cost (öre) of the paid staff time of all room sessions as a linear expression, or 0 when it is not priced."""
    if not paid_time_active(problem):
        return 0
    prep, closing = problem.staffing.preparation_minutes, problem.staffing.closing_minutes
    minimum = problem.staffing.min_paid_minutes
    max_staff = problem.staffing.ladder[-1].required_staff
    terms = []
    for room in problem.rooms:
        for slot in problem.slots:
            key = room.room_id, slot.slot_id
            active = variables.sessions[key]
            high = slot.latest_end_minute - slot.start_minute + prep + closing
            name = f"{room.room_id}_{slot.slot_id}"
            work = model.NewIntVar(0, high, f"work_{name}")
            model.Add(work == variables.session_end[key] - slot.start_minute + prep + closing).OnlyEnforceIf(active)
            model.Add(work == 0).OnlyEnforceIf(active.Not())
            core_high = max(high, minimum)
            core = work
            if minimum > 0:
                core = model.NewIntVar(0, core_high, f"paid_core_{name}")
                model.AddMaxEquality(core, [work, minimum * active])
            length = model.NewIntVar(0, core_high + room.travel_paid_minutes, f"paid_len_{name}")
            model.Add(length == core + room.travel_paid_minutes * active)
            minutes = model.NewIntVar(0, max_staff * (core_high + room.travel_paid_minutes), f"paid_min_{name}")
            model.AddMultiplicationEquality(minutes, [variables.staff[key], length])
            terms.append(minutes)
    return problem.staffing.paid_minute_cost_ore * sum(terms)
