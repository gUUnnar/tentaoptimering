"""Demand, scope and calendar rules checked on the saved schedule."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from .context import Context, Demand, Slot
from .derive import clock
from .report import FAIL, NOT_APPLICABLE, NOT_EVALUATED, PASS, TECHNICAL, RuleResult, rule

_CALENDAR_PARAMETERS = (
    "window.earlier_days", "window.later_days", "calendar.weekdays", "calendar.blocked_ranges",
    "calendar.start_times", "calendar.earliest_start_time", "calendar.latest_end_time",
    "calendar.start_date", "calendar.end_date",
)


def _no_solution(rule_id: str, reference: str) -> RuleResult:
    return rule(rule_id, TECHNICAL, NOT_APPLICABLE, "Resultatet innehåller ingen lösning att validera.", reference=reference)


def demand_rules(ctx: Context) -> list[RuleResult]:
    if not ctx.has_solution:
        outcome = ctx.result["solver"]["outcome"]
        partial = bool(ctx.result.get("schedule") or ctx.result.get("assignments") or ctx.result.get("costs"))
        return [
            _no_solution("each_demand_scheduled_once", "krav: varje behov exakt en gång"),
            rule(
                "no_partial_placement", TECHNICAL, FAIL if partial else PASS,
                "Ett resultat utan lösning innehåller en partiell placering eller kostnad." if partial
                else f"Utfallet `{outcome}` innehåller ingen partiell placering.",
                reference="krav: ingen partiell placering",
            ),
        ]
    raw = [str(row.get("exam_demand_id")) for row in ctx.result.get("schedule", ())]
    counts = Counter(raw)
    missing = sorted(set(ctx.demands) - set(counts))
    extra = sorted(set(counts) - set(ctx.demands))
    repeated = sorted(key for key, value in counts.items() if value > 1)
    results = [rule(
        "each_demand_scheduled_once", TECHNICAL, FAIL if (missing or extra or repeated) else PASS,
        f"saknas: {len(missing)}, okända: {len(extra)}, flera gånger: {len(repeated)}" if (missing or extra or repeated)
        else f"Alla {len(ctx.demands)} behov förekommer exakt en gång.",
        missing + extra + repeated, "krav: varje behov exakt en gång",
    )]
    results.append(_participants(ctx))
    results.append(_no_double_counting(ctx))
    results.append(_non_room(ctx))
    results.append(_coverage(ctx))
    results.append(_scope(ctx))
    return results


def _participants(ctx: Context) -> RuleResult:
    placed: Counter[str] = Counter()
    for row in ctx.assignments:
        placed[str(row.get("exam_demand_id"))] += int(row.get("participants", 0))
    wrong = [
        f"{item.demand_id} ({placed[item.demand_id]}/{item.participants})"
        for item in ctx.demands.values() if item.requires_room and placed[item.demand_id] != item.participants
    ]
    scheduled_wrong = [
        item.demand_id for item in ctx.demands.values()
        if item.demand_id in ctx.schedule and int(ctx.schedule[item.demand_id].get("participants", -1)) != item.participants
    ]
    problems = wrong + [f"{item} (schemarad)" for item in scheduled_wrong]
    return rule(
        "participants_placed", TECHNICAL, FAIL if problems else PASS,
        "Deltagare per tentamen och sal summerar inte till behovets antal." if problems
        else "Summan av deltagare per sal är lika med behovets deltagarantal för varje tentamen med lokalbehov.",
        problems, "krav: alla obligatoriska deltagare placerade",
    )


def _no_double_counting(ctx: Context) -> RuleResult:
    activities = Counter(activity for item in ctx.demands.values() for activity in item.source_activities)
    groups = Counter(group for item in ctx.demands.values() for group in item.group_ids)
    duplicates = [f"aktivitet {key}" for key, value in activities.items() if value > 1]
    duplicates += [f"grupp {key}" for key, value in groups.items() if value > 1]
    return rule(
        "no_double_counting", TECHNICAL, FAIL if duplicates else PASS,
        "Källaktiviteter eller deltagargrupper förekommer flera gånger." if duplicates
        else "Varje källaktivitet och deltagargrupp räknas högst en gång.",
        duplicates, "krav: källaktiviteter räknas inte dubbelt",
    )


def _non_room(ctx: Context) -> RuleResult:
    non_room = [item.demand_id for item in ctx.demands.values() if not item.requires_room]
    placed = sorted({str(row.get("exam_demand_id")) for row in ctx.assignments} & set(non_room))
    if not non_room:
        return rule("non_room_demands", TECHNICAL, NOT_APPLICABLE, "Inga behov saknar lokalbehov.")
    return rule(
        "non_room_demands", TECHNICAL, FAIL if placed else PASS,
        "Behov utan lokalbehov har fått en fysisk placering." if placed
        else f"{len(non_room)} behov utan lokalbehov kräver ingen sal och har ingen.",
        placed or non_room, "krav: hemtentor kräver inte fysisk placering",
    )


def _coverage(ctx: Context) -> RuleResult:
    coverage = ctx.result.get("coverage", {})
    total = sum(item.participants for item in ctx.demands.values())
    assigned = sum(int(row.get("participants", 0)) for row in ctx.assignments)
    non_room = sum(item.participants for item in ctx.demands.values() if not item.requires_room)
    expected = {
        "exam_demands_total": len(ctx.demands), "exam_demands_scheduled": len(set(ctx.schedule) & set(ctx.demands)),
        "participants_total": total, "participants_assigned_to_rooms": assigned,
        "non_room_participants_scheduled": non_room,
        "technical_placement_complete": len(set(ctx.schedule) & set(ctx.demands)) == len(ctx.demands)
        and assigned + non_room == total,
    }
    wrong = [key for key, value in expected.items() if coverage.get(key) != value]
    return rule(
        "coverage_reported_correctly", TECHNICAL, FAIL if wrong else PASS,
        f"Rapporterad täckning avviker i: {', '.join(wrong)}." if wrong else "Rapporterad täckning stämmer med omräkning.",
        wrong, "krav: täckning redovisas korrekt",
    )


def _scope(ctx: Context) -> RuleResult:
    scope = ctx.problem.get("scope", {})
    unresolved = int(scope.get("unresolved_source_activities", 0))
    limitations = " ".join(str(item) for item in ctx.result.get("limitations", ()))
    problems = []
    if scope.get("modeled_exam_demands") != len(ctx.demands):
        problems.append("modeled_exam_demands")
    if scope.get("modeled_participants") != sum(item.participants for item in ctx.demands.values()):
        problems.append("modeled_participants")
    if unresolved and str(unresolved) not in limitations:
        problems.append(f"{unresolved} oavgjorda aktiviteter redovisas inte i resultatets begränsningar")
    return rule(
        "scope_disclosed", TECHNICAL, FAIL if problems else PASS,
        "Omfattningen stämmer inte eller oavgjorda aktiviteter döljs." if problems
        else (f"Omfattningen stämmer; {unresolved} oavgjorda aktiviteter utanför omfattningen redovisas separat."
              if unresolved else "Omfattningen stämmer; inga oavgjorda aktiviteter."),
        problems, "krav: oavgjorda aktiviteter redovisas separat",
    )


def _blocked(value: object) -> list[tuple[date, date]]:
    return [(date.fromisoformat(str(item["start"])), date.fromisoformat(str(item["end"]))) for item in (value or [])]


def _allowed(
    slot: Slot, demand: Demand, p: dict, bounds: tuple[date, date], blocked: list[tuple[date, date]],
) -> list[str]:
    """Every user setting a movable exam must respect, listed when violated."""
    broken = []
    if slot.reference_only:
        broken.append("referenspass används som alternativ")
    if demand.original_day is not None:
        shift = (slot.day - demand.original_day).days
        if shift < -int(p["window.earlier_days"]) or shift > int(p["window.later_days"]):
            broken.append(f"utanför flyttfönstret ({shift:+d} dagar)")
    if slot.day.isoweekday() not in {int(item) for item in p["calendar.weekdays"]}:
        broken.append(f"otillåten veckodag {slot.day.isoweekday()}")
    if any(low <= slot.day <= high for low, high in blocked):
        broken.append("spärrat datum")
    if not bounds[0] <= slot.day <= bounds[1]:
        broken.append("utanför datumgränserna")
    if slot.start < clock(p["calendar.earliest_start_time"]):
        broken.append("före tidigaste starttid")
    if slot.start not in {clock(item) for item in p["calendar.start_times"]}:
        broken.append("otillåten starttid")
    if slot.start + demand.duration > clock(p["calendar.latest_end_time"]):
        broken.append("slutar efter senaste sluttid")
    if slot.start + demand.duration > slot.latest_end:
        broken.append("slutar efter passets egen sluttidsgräns")
    if demand.candidates and slot.slot_id not in demand.candidates:
        broken.append("inte bland behovets kandidater")
    return broken


def _bounds(ctx: Context, p: dict) -> tuple[date, date]:
    originals = [item.original_day for item in ctx.demands.values() if item.original_day is not None]
    first = date.fromisoformat(str(p["calendar.start_date"])) if p["calendar.start_date"] else (
        min(originals) - timedelta(days=int(p["window.earlier_days"])) if originals else date.min)
    last = date.fromisoformat(str(p["calendar.end_date"])) if p["calendar.end_date"] else (
        max(originals) + timedelta(days=int(p["window.later_days"])) if originals else date.max)
    return first, last


def calendar_rules(ctx: Context) -> list[RuleResult]:
    if not ctx.has_solution:
        return [_no_solution(item, "krav: kalender") for item in (
            "movable_exams_follow_calendar", "fixed_exams_keep_history", "slot_catalogue", "candidate_generation",
            "slot_end_limit", "course_conflicts")]
    missing = [name for name in _CALENDAR_PARAMETERS if name not in ctx.parameters]
    results = [_fixed_exams(ctx), _slot_end_limit(ctx)]
    if missing:
        reason = "Kalenderparametrar saknas i indata: " + ", ".join(missing)
        return results + [rule(name, TECHNICAL, NOT_EVALUATED, reason, missing, "krav: kalender") for name in (
            "movable_exams_follow_calendar", "slot_catalogue", "candidate_generation")] + [_conflicts(ctx)]
    p = ctx.parameters
    bounds, blocked = _bounds(ctx, p), _blocked(p["calendar.blocked_ranges"])
    results += [_movable(ctx, p, bounds, blocked), _catalogue(ctx, p, bounds, blocked),
                _candidates(ctx, p, bounds, blocked), _conflicts(ctx)]
    return results


def _movable(ctx: Context, p: dict, bounds, blocked) -> RuleResult:
    broken, unknown_original = [], []
    movable = [item for item in ctx.demands.values() if item.movable]
    for item in movable:
        slot = ctx.slot_of(item.demand_id)
        if slot is None:
            broken.append(f"{item.demand_id}: okänt pass")
            continue
        if item.original_day is None:
            unknown_original.append(item.demand_id)
        problems = _allowed(slot, item, p, bounds, blocked)
        if problems:
            broken.append(f"{item.demand_id}: {'; '.join(problems)}")
    if not movable:
        return rule("movable_exams_follow_calendar", TECHNICAL, NOT_APPLICABLE, "Inga flyttbara tentamina.")
    if broken:
        return rule("movable_exams_follow_calendar", TECHNICAL, FAIL, f"{len(broken)} flyttbara tentamina bryter mot kalenderinställningarna.", broken, "krav: flyttfönster, veckodagar, spärrar, sluttid")
    if unknown_original:
        return rule("movable_exams_follow_calendar", TECHNICAL, NOT_EVALUATED, "Flyttfönstret kan inte prövas utan historiskt tillfälle.", unknown_original, "krav: flyttfönster")
    return rule("movable_exams_follow_calendar", TECHNICAL, PASS, f"{len(movable)} flyttbara tentamina ligger inom fönster, veckodagar, spärrar, starttider och sluttid. Historiskt tillfälle godtas inte automatiskt.", reference="krav: flyttfönster, veckodagar, spärrar, sluttid")


def _slot_end_limit(ctx: Context) -> RuleResult:
    """Every scheduled exam, fixed or movable, must end within its own slot's latest end."""
    broken = []
    for item in ctx.demands.values():
        slot = ctx.slot_of(item.demand_id)
        if slot is None:
            broken.append(f"{item.demand_id}: okänt pass")
        elif slot.start + item.duration > slot.latest_end:
            broken.append(f"{item.demand_id}@{slot.slot_id}: slut {slot.start + item.duration} > {slot.latest_end}")
    return rule(
        "slot_end_limit", TECHNICAL, FAIL if broken else PASS,
        "Tentamen slutar efter det valda passets egen sluttidsgräns." if broken
        else "Varje tentamen slutar inom det valda passets egen sluttidsgräns.",
        broken, "krav: senaste sluttid per pass",
    )


def _fixed_exams(ctx: Context) -> RuleResult:
    fixed = [item for item in ctx.demands.values() if not item.movable]
    if not fixed:
        return rule("fixed_exams_keep_history", TECHNICAL, NOT_APPLICABLE, "Inga uttryckligen oflyttbara tentamina.")
    broken, unknown = [], []
    for item in fixed:
        slot = ctx.slot_of(item.demand_id)
        if slot is None:
            broken.append(item.demand_id)
        elif item.original_day is not None and item.original_start is not None:
            if (slot.day, slot.start) != (item.original_day, int(item.original_start)):
                broken.append(item.demand_id)
        elif item.original_slot_id is not None:
            if slot.slot_id != item.original_slot_id:
                broken.append(item.demand_id)
        else:
            unknown.append(item.demand_id)
    if broken:
        return rule("fixed_exams_keep_history", TECHNICAL, FAIL, "Oflyttbara tentamina ligger inte på sitt historiska tillfälle.", broken, "krav: oflyttbara behåller historiskt tillfälle")
    if unknown:
        return rule("fixed_exams_keep_history", TECHNICAL, NOT_EVALUATED, "Historiskt tillfälle saknas i indata.", unknown)
    return rule("fixed_exams_keep_history", TECHNICAL, PASS, f"{len(fixed)} oflyttbara tentamina ligger på sitt historiska datum och sin starttid.", reference="krav: oflyttbara behåller historiskt tillfälle")


def _catalogue(ctx: Context, p: dict, bounds, blocked) -> RuleResult:
    broken = []
    fixed_keys = {(item.original_day, item.original_start) for item in ctx.demands.values() if not item.movable}
    weekdays = {int(item) for item in p["calendar.weekdays"]}
    starts = {clock(item) for item in p["calendar.start_times"]}
    for slot in ctx.slots.values():
        if slot.reference_only:
            if (slot.day, slot.start) not in fixed_keys:
                broken.append(f"{slot.slot_id}: fiktivt referenspass")
            continue
        if (slot.day.isoweekday() not in weekdays or any(low <= slot.day <= high for low, high in blocked)
                or not bounds[0] <= slot.day <= bounds[1] or slot.start not in starts
                or slot.start < clock(p["calendar.earliest_start_time"])):
            broken.append(f"{slot.slot_id}: bryter mot kalenderinställningarna")
    return rule(
        "slot_catalogue", TECHNICAL, FAIL if broken else PASS,
        "Passkatalogen innehåller otillåtna eller fiktiva pass." if broken
        else "Alla pass följer kalenderinställningarna; referenspass finns bara för oflyttbara tentamina.",
        broken, "krav: tillåtna datum och starttider",
    )


def _candidates(ctx: Context, p: dict, bounds, blocked) -> RuleResult:
    broken = []
    for item in ctx.demands.values():
        if not item.movable:
            slots = [ctx.slots[value] for value in item.candidates if value in ctx.slots]
            if any((slot.day, slot.start) != (item.original_day, item.original_start) for slot in slots if item.original_day):
                broken.append(f"{item.demand_id}: oflyttbar med andra kandidater än historiken")
            continue
        listed = {value for value in item.candidates}
        expected = {
            slot.slot_id for slot in ctx.slots.values()
            if not _allowed(slot, Demand(**{**item.__dict__, "candidates": frozenset()}), p, bounds, blocked)
        }
        if listed != expected:
            broken.append(f"{item.demand_id}: {len(listed - expected)} otillåtna, {len(expected - listed)} saknade kandidater")
    return rule(
        "candidate_generation", TECHNICAL, FAIL if broken else PASS,
        "Kandidatlistan avviker från en självständig omräkning ur parametrarna." if broken
        else "Kandidatlistorna är identiska med en självständig omräkning ur parametrarna.",
        broken, "krav: kandidater följer användarens inställningar",
    )


def _conflicts(ctx: Context) -> RuleResult:
    groups: dict[str, list[Demand]] = defaultdict(list)
    for item in ctx.demands.values():
        if item.course_code:
            groups[f"course:{item.course_code}"].append(item)
        for key in item.conflict_groups:
            groups[str(key)].append(item)
    pairs = set()
    for key, members in groups.items():
        unique = {item.demand_id: item for item in members}.values()
        slotted = [(item, ctx.slot_of(item.demand_id)) for item in unique]
        for index, (left, left_slot) in enumerate(slotted):
            for right, right_slot in slotted[index + 1:]:
                if left_slot and right_slot and left_slot.day == right_slot.day and (
                        left_slot.start < right_slot.start + right.duration and right_slot.start < left_slot.start + left.duration):
                    pairs.add(" / ".join(sorted((left.demand_id, right.demand_id))) + f" ({key})")
    if not groups:
        return rule("course_conflicts", TECHNICAL, NOT_EVALUATED, "Inga kurskoder eller konfliktgrupper finns i indata; ingen krockkontroll är möjlig.", reference="krav: kurskrockar")
    return rule(
        "course_conflicts", TECHNICAL, FAIL if pairs else PASS,
        f"{len(pairs)} par med samma kurs eller konfliktgrupp överlappar i tid." if pairs
        else "Inga tentamina i samma kurs eller uttrycklig konfliktgrupp överlappar. Studentöverlapp kontrolleras inte.",
        sorted(pairs), "krav: kurskrockar och uttryckliga konfliktgrupper",
    )
