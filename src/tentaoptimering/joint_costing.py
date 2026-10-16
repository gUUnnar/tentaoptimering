"""Cost and paid staff time of an optimiser result, derived by rule from its room sessions.

The rules live in `joint_pricing`, which prices any placement (an optimised plan or the actual booking) by the rules of a saved
problem. This module adapts the optimiser's own room-session rows (`slot_id`, `required_staff`, `available_again_minute`) to
them, so that the solver paths report the paid time of a solution and price a decomposed solution by exactly the rules that the
comparison of two alternatives uses. The independent post-validation has its own implementation (`joint_validation.derive`) and
does not import this one.

A *staff position* is one person at one room session, from `start - preparation` to `end + closing`. It is one paid pass:

    paid minutes = max(worked minutes, minimum paid minutes) + the room's travel minutes

`worked` is preparation, writing time of the longest exam in the room, and closing. The minimum is the shortest paid pass
(the collective agreement counts a pass under two hours as two). Travel is the paid time to and from a room outside the
staff's base. Each position is its own pass: the gaps between a person's passes on one day are not paid, because the pass is
not continuous. Whether a person can work several passes in a day is a staffing-rule question (`staffing.max_daily_minutes`
and the rest-time rules are not modelled), and an unmodelled rule is never reported as met.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .joint_contract import JointOptimizationInput
from .joint_pricing import PricedSession, passes, price, reserved_rooms, sessions_from_result

SUMMARY_BASIS = ("Varje vaktposition i ett salstillfälle är ett eget betalt pass från förberedelse till avslut, lägst kortaste betalda pass, plus salens betalda restid. "
                 "Luckor mellan en persons pass betalas inte; individuella arbetstids- och viloregler ingår inte.")


def priced_sessions(problem: JointOptimizationInput, rows: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> list[PricedSession]:
    """The room-session rows of a result as priced sessions."""
    return sessions_from_result(problem, {"room_sessions": list(rows)})


def paid_cost_ore(problem: JointOptimizationInput, rows: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> int:
    return problem.staffing.paid_minute_cost_ore * sum(item["paid_minutes"] for item in passes(problem, priced_sessions(problem, rows)))


def staffing_summary(problem: JointOptimizationInput, rows: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> dict[str, Any]:
    """Positions (paid passes), paid minutes and their parts, in total and per day and room; the cost follows from them."""
    tasks = passes(problem, priced_sessions(problem, rows))
    per_day: dict[str, dict[str, int]] = defaultdict(lambda: {"passes": 0, "paid_minutes": 0})
    per_room: dict[str, dict[str, int]] = defaultdict(lambda: {"passes": 0, "paid_minutes": 0})
    for row in tasks:
        for table, key in ((per_day, row["date"]), (per_room, row["room_id"])):
            table[key]["passes"] += 1
            table[key]["paid_minutes"] += row["paid_minutes"]
    paid = sum(row["paid_minutes"] for row in tasks)
    return {
        "unit": "staff_position_pass", "passes": len(tasks), "paid_minutes": paid, "worked_minutes": sum(row["worked_minutes"] for row in tasks),
        "minimum_top_up_minutes": sum(row["minimum_top_up_minutes"] for row in tasks), "travel_minutes": sum(row["travel_minutes"] for row in tasks),
        "paid_minute_cost_ore": problem.staffing.paid_minute_cost_ore, "paid_time_cost_ore": problem.staffing.paid_minute_cost_ore * paid,
        "per_day": dict(sorted(per_day.items())), "per_room": dict(sorted(per_room.items())), "basis": SUMMARY_BASIS,
    }


def reserved_room_ids(problem: JointOptimizationInput) -> set[str]:
    """Rooms that a blocking reservation uses: they are in use (and cost) even if no optimised exam sits there."""
    return reserved_rooms(problem)


def cost_of_sessions(problem: JointOptimizationInput, rows: list[dict[str, Any]] | tuple[dict[str, Any], ...], pool: int | None = None) -> dict[str, int]:
    """The cost components of a plan given as room-session rows, by the rules of the problem. `pool` replaces the computed peak staff."""
    priced = price(problem, priced_sessions(problem, rows))
    if pool is not None:
        pool_cost = problem.staffing.annual_cost_ore_per_staff * pool
        priced = {**priced, "comparable_total_cost_ore": priced["comparable_total_cost_ore"] - priced["annual_staff_pool_cost_ore"] + pool_cost, "annual_staff_pool_cost_ore": pool_cost}
    return priced
