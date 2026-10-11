"""Independent reconstruction of sessions, staffing and costs from the saved assignments.

Everything here is derived from the saved placement and the saved input values. The staffing
ladder, the staffing timeline and the cost sums are implemented here from their definition and
share no code with the optimizer.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from .context import Context


@dataclass(frozen=True)
class Session:
    room_id: str
    slot_id: str
    day: date
    start: int
    end: int
    demand_ids: tuple[str, ...]
    participants: int


def clock(value: str) -> int:
    hour, minute = str(value).split(":")
    return int(hour) * 60 + int(minute)


def staff_for(occupancy: int, ladder: list[tuple[int, int]]) -> int | None:
    """Staff required for an occupancy; None when the ladder does not cover it."""
    if occupancy <= 0:
        return 0
    for limit, staff in ladder:
        if occupancy <= limit:
            return staff
    return None


def build_sessions(ctx: Context) -> dict[tuple[str, str], Session]:
    """One session per (room, slot) holding at least one assigned participant."""
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in ctx.assignments:
        try:
            key = str(row["room_id"]), str(row["slot_id"])
            int(row["participants"])
        except (KeyError, TypeError, ValueError):
            continue
        grouped[key].append(row)
    sessions = {}
    for (room_id, slot_id), rows in grouped.items():
        slot = ctx.slots.get(slot_id)
        if slot is None:
            continue
        demand_ids = sorted({str(row["exam_demand_id"]) for row in rows})
        durations = [ctx.demands[item].duration for item in demand_ids if item in ctx.demands]
        sessions[room_id, slot_id] = Session(
            room_id, slot_id, slot.day, slot.start, slot.start + (max(durations) if durations else 0),
            tuple(demand_ids), sum(int(row["participants"]) for row in rows),
        )
    return sessions


def staff_by_session(ctx: Context, sessions: dict[tuple[str, str], Session]) -> dict[tuple[str, str], int | None]:
    return {key: staff_for(item.participants, ctx.ladder) for key, item in sessions.items()}


def peak_concurrent_staff(
    ctx: Context, sessions: dict[tuple[str, str], Session], staff: dict[tuple[str, str], int | None]
) -> tuple[int, str | None]:
    """Maximum simultaneous staff over the timeline; each session is active [start - prep, end + closing)."""
    by_day: dict[date, list[tuple[int, int]]] = defaultdict(list)
    for key, session in sessions.items():
        need = staff.get(key) or 0
        if need:
            by_day[session.day].append((session.start - ctx.preparation, need))
            by_day[session.day].append((session.end + ctx.closing, -need))
    peak, peak_day = 0, None
    for day, events in by_day.items():
        running = 0
        for _time, delta in sorted(events):  # at equal times ends (negative) are processed first
            running += delta
            if running > peak:
                peak, peak_day = running, day.isoformat()
    return peak, peak_day


def recompute_costs(
    ctx: Context, sessions: dict[tuple[str, str], Session], staff: dict[tuple[str, str], int | None], pool: int
) -> dict[str, int]:
    used_rooms = {room_id for room_id, _slot in sessions}
    per_room_sessions: dict[str, int] = defaultdict(int)
    for room_id, _slot in sessions:
        per_room_sessions[room_id] += 1
    room_cost = sum(ctx.rooms[room_id].fixed_cost for room_id in used_rooms if room_id in ctx.rooms)
    external = sum(
        ctx.rooms[room_id].external_cost * count for room_id, count in per_room_sessions.items() if room_id in ctx.rooms
    )
    pool_cost = ctx.staff_annual_cost * pool
    session_cost = ctx.staff_session_cost * sum(value or 0 for value in staff.values())
    return {
        "annual_room_cost_ore": room_cost,
        "external_room_session_cost_ore": external,
        "annual_staff_pool_cost_ore": pool_cost,
        "staff_session_cost_ore": session_cost,
        "comparable_total_cost_ore": room_cost + external + pool_cost + session_cost,
    }
