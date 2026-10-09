"""Room rules checked on the saved assignments."""

from __future__ import annotations

from collections import Counter, defaultdict

from .context import Context
from .derive import Session, build_sessions, staff_by_session
from .report import FAIL, NOT_APPLICABLE, PASS, TECHNICAL, RuleResult, rule

_ROOM_RULES = (
    "assignments_wellformed", "room_planning_area", "room_capacity", "room_availability", "rooms_per_exam",
    "building_split", "room_turnaround_and_double_booking", "digital_compatibility_technical", "room_sessions_reconstructed",
)


def room_rules(ctx: Context) -> list[RuleResult]:
    if not ctx.has_solution:
        return [rule(name, TECHNICAL, NOT_APPLICABLE, "Resultatet innehåller ingen lösning att validera.") for name in _ROOM_RULES]
    sessions = build_sessions(ctx)
    return [
        _wellformed(ctx), _area(ctx), _capacity(ctx, sessions), _availability(ctx), _rooms_per_exam(ctx),
        _buildings(ctx), _turnaround(ctx, sessions), _digital(ctx), _reconstructed(ctx, sessions),
    ]


def _rows(ctx: Context) -> list[tuple[dict, str, str, str, int]]:
    rows = []
    for row in ctx.assignments:
        try:
            rows.append((row, str(row["exam_demand_id"]), str(row["slot_id"]), str(row["room_id"]), int(row["participants"])))
        except (KeyError, TypeError, ValueError):
            rows.append((row, "", "", "", -1))
    return rows


def _wellformed(ctx: Context) -> RuleResult:
    broken, seen = [], Counter()
    for _row, demand_id, slot_id, room_id, count in _rows(ctx):
        label = f"{demand_id or '?'}@{room_id or '?'}"
        if count <= 0 or not demand_id:
            broken.append(f"{label}: ogiltig rad")
            continue
        seen[demand_id, room_id] += 1
        demand = ctx.demands.get(demand_id)
        if demand is None:
            broken.append(f"{label}: okänt behov")
        elif ctx.schedule.get(demand_id, {}).get("slot_id") != slot_id:
            broken.append(f"{label}: sal på annat pass än schemat")
        if room_id not in ctx.rooms:
            broken.append(f"{label}: fiktiv eller okänd sal")
    broken += [f"{demand}@{room}: dubblettrad" for (demand, room), value in seen.items() if value > 1]
    return rule("assignments_wellformed", TECHNICAL, FAIL if broken else PASS,
                "Salsplaceringar saknar behov, pass eller sal i indata, eller är dubbletter." if broken
                else "Varje salsplacering hör till ett känt behov, schemats pass och en sal som finns i indata.",
                broken, "krav: inga fiktiva lokaler")


def _area(ctx: Context) -> RuleResult:
    broken = [
        f"{demand_id}@{room_id}" for _row, demand_id, _slot, room_id, _count in _rows(ctx)
        if demand_id in ctx.demands and room_id in ctx.rooms and ctx.demands[demand_id].area != ctx.rooms[room_id].area
    ]
    return rule("room_planning_area", TECHNICAL, FAIL if broken else PASS,
                "Tentamen placerad i sal i annat planeringsområde." if broken
                else "Alla placeringar ligger i tentamens planeringsområde.", broken, "krav: Uppsala och Visby hålls isär")


def _capacity(ctx: Context, sessions: dict[tuple[str, str], Session]) -> RuleResult:
    broken = [
        f"{room_id}@{slot_id} ({item.participants}/{ctx.rooms[room_id].capacity})"
        for (room_id, slot_id), item in sessions.items()
        if room_id in ctx.rooms and item.participants > ctx.rooms[room_id].capacity
    ]
    return rule("room_capacity", TECHNICAL, FAIL if broken else PASS,
                "Salens fysiska kapacitet överskrids." if broken
                else "Ingen sal har fler deltagare än sin kapacitet vid något salstillfälle.", broken, "krav: fysisk kapacitet är ett absolut tak")


def _availability(ctx: Context) -> RuleResult:
    broken = [
        f"{room_id}@{slot_id}" for _row, _demand, slot_id, room_id, _count in _rows(ctx)
        if room_id in ctx.rooms and ctx.rooms[room_id].available_slots is not None and slot_id not in ctx.rooms[room_id].available_slots
    ]
    return rule("room_availability", TECHNICAL, FAIL if sorted(set(broken)) else PASS,
                "Sal används ett pass då den inte är tillgänglig enligt indata." if broken
                else "Alla salstillfällen ligger inom salens tillgänglighet enligt indata.", broken, "krav: salstillgänglighet")


def _rooms_per_exam(ctx: Context) -> RuleResult:
    rooms: dict[str, set[str]] = defaultdict(set)
    for _row, demand_id, _slot, room_id, _count in _rows(ctx):
        rooms[demand_id].add(room_id)
    broken = [f"{key} ({len(value)}>{ctx.demands[key].max_rooms})" for key, value in rooms.items()
              if key in ctx.demands and len(value) > ctx.demands[key].max_rooms]
    return rule("rooms_per_exam", TECHNICAL, FAIL if broken else PASS,
                "Tentamen delad över fler salar än tillåtet." if broken
                else "Ingen tentamen använder fler salar än sitt tillåtna högsta antal.", broken, "krav: högsta antal salar per tenta")


def _buildings(ctx: Context) -> RuleResult:
    buildings: dict[str, set[str]] = defaultdict(set)
    for _row, demand_id, _slot, room_id, _count in _rows(ctx):
        if room_id in ctx.rooms:
            buildings[demand_id].add(ctx.rooms[room_id].building)
    broken = [key for key, value in buildings.items()
              if key in ctx.demands and not ctx.demands[key].split_across_buildings and len(value) > 1]
    return rule("building_split", TECHNICAL, FAIL if broken else PASS,
                "Tentamen delad över flera byggnader trots förbud." if broken
                else "Ingen tentamen delas över flera byggnader där det är förbjudet.", broken, "krav: byggnadsdelning")


def _turnaround(ctx: Context, sessions: dict[tuple[str, str], Session]) -> RuleResult:
    by_room: dict[str, list[Session]] = defaultdict(list)
    for item in sessions.values():
        by_room[item.room_id].append(item)
    broken = []
    for room_id, items in by_room.items():
        latest_end: dict = {}
        for item in sorted(items, key=lambda value: (value.day, value.start)):
            end = latest_end.get(item.day)
            if end is not None and item.start < end + ctx.turnaround:
                broken.append(f"{room_id}@{item.slot_id}: start {item.start} < {end}+{ctx.turnaround}")
            latest_end[item.day] = max(end or 0, item.end)
    return rule("room_turnaround_and_double_booking", TECHNICAL, FAIL if broken else PASS,
                "Två salstillfällen överlappar eller har för kort ställtid." if broken
                else f"Inga dubbelbokningar; ställtiden {ctx.turnaround} minuter hålls mellan alla salstillfällen.",
                broken, "krav: ställtid och inga dubbelbokningar")


def _digital(ctx: Context) -> RuleResult:
    broken = [
        f"{demand_id}@{room_id}" for _row, demand_id, _slot, room_id, _count in _rows(ctx)
        if demand_id in ctx.demands and room_id in ctx.rooms and ctx.demands[demand_id].digital_requirement == "e_exam"
        and "e_exam" not in ctx.rooms[room_id].digital_capabilities
    ]
    return rule("digital_compatibility_technical", TECHNICAL, FAIL if broken else PASS,
                "Digital tentamen placerad i sal utan digital kapabilitet i indata." if broken
                else "Alla digitala tentamina ligger i salar som är digitalkapabla enligt indata.",
                broken, "krav: digital kompatibilitet (hårt villkor enligt indata)")


def _reconstructed(ctx: Context, sessions: dict[tuple[str, str], Session]) -> RuleResult:
    reported = {(str(row.get("room_id")), str(row.get("slot_id"))): row for row in ctx.sessions}
    staff = staff_by_session(ctx, sessions)
    broken = [f"{room}@{slot}: saknas i rapporten" for room, slot in sessions if (room, slot) not in reported]
    broken += [f"{room}@{slot}: finns inte i placeringen" for room, slot in reported if (room, slot) not in sessions]
    for key, item in sessions.items():
        row = reported.get(key)
        if row is None:
            continue
        expected = {
            "participants": item.participants, "exam_demand_ids": list(item.demand_ids),
            "available_again_minute": item.end + ctx.turnaround, "required_staff": staff.get(key),
        }
        broken += [f"{key[0]}@{key[1]}: {name}" for name, value in expected.items() if row.get(name) != value]
        if ctx.rooms.get(key[0]) and row.get("building_id") != ctx.rooms[key[0]].building:
            broken.append(f"{key[0]}@{key[1]}: building_id")
    return rule("room_sessions_reconstructed", TECHNICAL, FAIL if broken else PASS,
                "Rapporterade salstillfällen avviker från en omräkning ur placeringen." if broken
                else f"Alla {len(sessions)} rapporterade salstillfällen stämmer med omräkning (deltagare, behov, sluttid, vakter).",
                broken, "krav: härledda resultat räknas om")
