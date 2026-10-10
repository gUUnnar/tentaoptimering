"""Business verification: which rules rest on verified evidence, and which do not.

A technically correct placement is not business-verified. A rule gets `pass` only when every
parameter it depends on is verified or documented source data and has engine support. Missing
evidence or missing engine support gives `not_evaluated`, never `pass`.
"""

from __future__ import annotations

from .context import Context
from .report import BUSINESS, NOT_APPLICABLE, NOT_EVALUATED, PASS, RuleResult, rule

_EVIDENCE = {"verified", "source_data"}

_GROUPS = {
    "calendar_rules_verified": (
        "Kalenderregler", ("window.earlier_days", "window.later_days", "calendar.weekdays", "calendar.blocked_ranges",
                           "calendar.start_times", "calendar.earliest_start_time", "calendar.latest_end_time",
                           "calendar.start_date", "calendar.end_date", "calendar.exam_periods", "rules.keep_course_order")),
    "room_rules_verified": (
        "Lokalregler (kapacitet, tillgänglighet, urval)", ("rooms.selection", "rooms.max_rooms_per_exam", "rooms.allow_split",
                                                          "rooms.allow_split_across_buildings", "rooms.availability_mode",
                                                          "rooms.capacity_override", "rooms.custom_rooms", "rooms.co_location_rules",
                                                          "calendar.turnaround_minutes")),
    "staffing_rules_verified": (
        "Bemanningsregler", ("staffing.ladder", "staffing.preparation_minutes", "staffing.closing_minutes", "staffing.shifts",
                             "staffing.min_break_minutes", "staffing.max_continuous_minutes", "staffing.max_daily_minutes",
                             "staffing.min_daily_rest_minutes", "staffing.travel_minutes", "staffing.min_paid_shift_minutes")),
    "cost_basis_verified": (
        "Kostnadsgrund", ("cost.room_annual_per_seat_ore", "cost.staff_annual_ore", "cost.staff_session_ore",
                          "cost.external_room_session_ore", "cost.annualization_factor", "cost.avoidable_cost_definition")),
    "demand_basis_verified": (
        "Efterfrågegrund", ("demand.measure", "demand.variation_pct", "demand.rounding", "demand.capacity_safety_margin_pct")),
}


def _basis_rule(ctx: Context, rule_id: str, label: str, ids: tuple[str, ...]) -> RuleResult:
    absent = [item for item in ids if item not in ctx.parameter_meta]
    if absent:
        return rule(rule_id, BUSINESS, NOT_EVALUATED,
                    f"{label}: {len(absent)} av {len(ids)} parametrar saknar definition i indata, så grunden kan inte avgöras.",
                    absent, "krav: verifierad mot underlag")
    present = [ctx.parameter_meta[item] for item in ids]
    unsupported = [item["parameter_id"] for item in present if item.get("engine_support") != "implemented"]
    assumed = [item["parameter_id"] for item in present
               if item.get("engine_support") == "implemented" and item.get("basis") not in _EVIDENCE]
    if unsupported or assumed:
        parts = []
        if assumed:
            parts.append(f"{len(assumed)} vilar på antaganden eller experiment")
        if unsupported:
            parts.append(f"{len(unsupported)} saknar motorstöd")
        return rule(rule_id, BUSINESS, NOT_EVALUATED, f"{label}: {', '.join(parts)}. Tekniskt korrekt placering är inte verksamhetsmässigt verifierad.",
                    assumed + unsupported, "krav: verifierad mot underlag")
    return rule(rule_id, BUSINESS, PASS, f"{label}: alla parametrar är verifierade eller dokumenterad källdata och har motorstöd.", reference="krav: verifierad mot underlag")


def business_rules(ctx: Context) -> list[RuleResult]:
    results = [_basis_rule(ctx, rule_id, label, ids) for rule_id, (label, ids) in _GROUPS.items()]
    scope = ctx.problem.get("scope", {})
    unresolved = int(scope.get("unresolved_source_activities", 0))
    results.append(rule(
        "population_completeness", BUSINESS, NOT_EVALUATED if unresolved else PASS,
        f"Fullständig täckning gäller bara den modellerade omfattningen. {unresolved} oavgjorda källaktiviteter av "
        f"{scope.get('source_activities_total')} ligger utanför; resultatet säger inget om hela verksamheten." if unresolved
        else "Inga oavgjorda källaktiviteter; hela källpopulationen är modellerad.",
        reference="krav: omfattning redovisas, inte döljs",
    ))
    results.append(rule(
        "student_overlap", BUSINESS, NOT_EVALUATED,
        "Studentöverlapp och programkrockar kontrolleras inte (saknad data och motorstöd). Endast kurskod och uttryckliga konfliktgrupper prövas tekniskt.",
        reference="krav: studentkrockar (rules.student_conflicts är contract_only)",
    ))
    results.append(_digital(ctx))
    shared = [item.demand_id for item in ctx.demands.values() if item.group_basis != "single_activity"]
    results.append(rule(
        "group_disjointness", BUSINESS, NOT_EVALUATED if shared else NOT_APPLICABLE,
        f"{len(shared)} samtentor summerar deltagare från flera aktiviteter under antagande att grupperna är disjunkta." if shared
        else "Inga behov summerar flera källaktiviteter.", shared, "krav: gruppernas disjunkthet verifieras",
    ))
    unsupported = sorted(item["parameter_id"] for item in ctx.parameter_meta.values() if item.get("engine_support") != "implemented")
    changed = sorted(item["parameter_id"] for item in ctx.parameter_meta.values()
                     if item.get("engine_support") != "implemented" and item.get("changed_from_default"))
    results.append(rule(
        "unsupported_parameters", BUSINESS, NOT_EVALUATED if unsupported else NOT_APPLICABLE,
        (f"{len(unsupported)} definierade parametrar saknar motorstöd och påverkar inte lösningen"
         + (f"; {len(changed)} av dem har ändrats och ignoreras." if changed else ".")) if unsupported
        else "Alla parametrar har motorstöd.", changed or unsupported, "krav: parametrar utan motorstöd är aldrig godkända",
    ))
    return results


def _digital(ctx: Context) -> RuleResult:
    digital = [item for item in ctx.demands.values() if item.digital_requirement == "e_exam" and item.requires_room]
    if not digital:
        return rule("digital_compatibility_verified", BUSINESS, NOT_APPLICABLE, "Inga digitala tentamina med lokalbehov.")
    rooms_by_demand: dict[str, set[str]] = {}
    for row in ctx.assignments:
        rooms_by_demand.setdefault(str(row.get("exam_demand_id")), set()).add(str(row.get("room_id")))
    partial = sorted(
        item.demand_id for item in digital
        if any(room in ctx.rooms and ctx.rooms[room].digital_basis != "all_places" for room in rooms_by_demand.get(item.demand_id, ()))
    )
    uncertain = sorted(item.demand_id for item in digital if item.digital_basis in {"unobserved", "observed_mixed"})
    return rule(
        "digital_compatibility_verified", BUSINESS, NOT_EVALUATED,
        f"Ingen verifierad kompatibilitetsmatris finns (digital.compatibility_matrix saknar underlag). {len(digital)} digitala behov; "
        f"{len(partial)} ligger i salar med ej kvantifierat digitalstöd, {len(uncertain)} har okänd eller blandad digital status.",
        sorted(set(partial) | set(uncertain)) or [item.demand_id for item in digital], "krav: digital kompatibilitet verifieras mot underlag",
    )
