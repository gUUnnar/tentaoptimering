"""Staffing, cost, change-count and solver-report consistency rules."""

from __future__ import annotations

from .context import Context
from .derive import build_sessions, peak_concurrent_staff, recompute_costs, staff_by_session
from .report import FAIL, NOT_APPLICABLE, NOT_EVALUATED, PASS, TECHNICAL, RuleResult, rule

_NAMES = (
    "staffing_per_room_session", "staff_pool_covers_peak", "staff_pool_not_inflated", "costs_recomputed",
    "changed_exams_recomputed", "solver_report_consistent",
)


def staffing_cost_rules(ctx: Context) -> list[RuleResult]:
    if not ctx.has_solution:
        results = [rule(name, TECHNICAL, NOT_APPLICABLE, "Resultatet innehåller ingen lösning att validera.") for name in _NAMES[:5]]
        return results + [_solver_report(ctx)]
    sessions = build_sessions(ctx)
    staff = staff_by_session(ctx, sessions)
    peak, peak_day = peak_concurrent_staff(ctx, sessions, staff)
    pool = ctx.result.get("staff_pool_size")
    return [
        _per_session(ctx, sessions, staff), _covers_peak(pool, peak, peak_day), _not_inflated(ctx, pool, peak),
        _costs(ctx, sessions, staff, pool), _changed(ctx), _solver_report(ctx),
    ]


def _per_session(ctx: Context, sessions, staff) -> RuleResult:
    uncovered = [f"{room}@{slot}: {sessions[room, slot].participants} deltagare saknar trappsteg" for (room, slot), need in staff.items() if need is None]
    reported = {(str(row.get("room_id")), str(row.get("slot_id"))): row.get("required_staff") for row in ctx.sessions}
    wrong = [f"{room}@{slot}: rapporterat {reported[room, slot]}, beräknat {need}" for (room, slot), need in staff.items()
             if (room, slot) in reported and reported[room, slot] != need]
    broken = uncovered + wrong
    return rule("staffing_per_room_session", TECHNICAL, FAIL if broken else PASS,
                "Vaktbehovet per salstillfälle avviker från bemanningstrappan." if broken
                else f"Vaktbehovet för alla {len(sessions)} salstillfällen följer trappan {ctx.ladder} (gränser testade i valideringens egna tester).",
                broken, "krav: bemanningstrappa")


def _covers_peak(pool: object, peak: int, peak_day: str | None) -> RuleResult:
    if not isinstance(pool, int) or isinstance(pool, bool):
        return rule("staff_pool_covers_peak", TECHNICAL, FAIL, "Bemanningspoolen saknas eller är inte ett heltal.", reference="krav: pool täcker maximal samtidig efterfrågan")
    return rule("staff_pool_covers_peak", TECHNICAL, FAIL if pool < peak else PASS,
                f"Poolen {pool} är mindre än maximal samtidig bemanning {peak} ({peak_day})." if pool < peak
                else f"Poolen {pool} täcker maximal samtidig bemanning {peak}" + (f" ({peak_day})." if peak_day else "."),
                reference="krav: pool täcker maximal samtidig efterfrågan inklusive förberedelse och avslutning")


def _not_inflated(ctx: Context, pool: object, peak: int) -> RuleResult:
    outcome = ctx.result["solver"]["outcome"]
    if not isinstance(pool, int) or pool <= peak:
        return rule("staff_pool_not_inflated", TECHNICAL, PASS, "Poolen är inte större än behovet." if pool == peak else "Poolen är inte större än behovet.", reference="konsistens: optimalt resultat har ingen överflödig pool")
    inconsistent = outcome == "optimal" and ctx.staff_annual_cost > 0
    return rule("staff_pool_not_inflated", TECHNICAL, FAIL if inconsistent else PASS,
                f"Poolen {pool} är större än behovet {peak} trots utfallet `optimal` och poolkostnad > 0." if inconsistent
                else f"Poolen {pool} är större än behovet {peak}; ingen optimalitet påstås eller poolen är gratis.",
                reference="konsistens: optimalt resultat har ingen överflödig pool")


def _costs(ctx: Context, sessions, staff, pool: object) -> RuleResult:
    costs = ctx.result.get("costs")
    if not isinstance(costs, dict) or not isinstance(pool, int):
        return rule("costs_recomputed", TECHNICAL, FAIL, "Kostnader eller pool saknas i resultatet.", reference="krav: kostnader räknas om")
    expected = recompute_costs(ctx, sessions, staff, pool)
    broken = [f"{name}: rapporterat {costs.get(name)}, beräknat {value}" for name, value in expected.items() if costs.get(name) != value]
    parts = sum(int(costs.get(name, 0)) for name in expected if name != "comparable_total_cost_ore")
    if costs.get("comparable_total_cost_ore") != parts:
        broken.append(f"komponenterna summerar till {parts}, totalen är {costs.get('comparable_total_cost_ore')}")
    objective = ctx.result["solver"].get("objective_value_ore")
    if objective != costs.get("comparable_total_cost_ore"):
        broken.append(f"solvermålet {objective} avviker från modellkostnaden")
    return rule("costs_recomputed", TECHNICAL, FAIL if broken else PASS,
                "Kostnadskomponenter, summa eller solvermål avviker från omräkningen." if broken
                else f"Lokaler, externa salstillfällen, pool och rörlig bemanning räknas om och summerar till {expected['comparable_total_cost_ore']} öre.",
                broken, "krav: kostnaderna summerar till modellkostnaden")


def _changed(ctx: Context) -> RuleResult:
    changed, unknown = 0, []
    for item in ctx.demands.values():
        slot = ctx.slot_of(item.demand_id)
        if slot is None:
            continue
        if item.original_day is not None and item.original_start is not None:
            changed += (slot.day, slot.start) != (item.original_day, int(item.original_start))
        elif item.original_slot_id is not None:
            changed += slot.slot_id != item.original_slot_id
        else:
            unknown.append(item.demand_id)
    reported = ctx.result.get("changed_exam_demands")
    if reported != changed:
        return rule("changed_exams_recomputed", TECHNICAL, FAIL, f"Rapporterat antal flyttade är {reported}, omräknat {changed}.", reference="krav: antal flyttade räknas om")
    if unknown:
        return rule("changed_exams_recomputed", TECHNICAL, NOT_EVALUATED, "Vissa behov saknar historiskt tillfälle och räknas inte som flyttade.", unknown)
    return rule("changed_exams_recomputed", TECHNICAL, PASS, f"{changed} flyttade tentamina stämmer med ursprungligt och nytt datum och starttid.", reference="krav: antal flyttade räknas om")


def _solver_report(ctx: Context) -> RuleResult:
    solver, costs = ctx.result["solver"], ctx.result.get("costs")
    outcome, objective, bound, gap = solver.get("outcome"), solver.get("objective_value_ore"), solver.get("best_objective_bound_ore"), solver.get("relative_gap")
    problems = []
    if outcome == "optimal" and not (objective is not None and bound == objective and gap == 0):
        problems.append("optimal kräver gräns lika med mål och gap 0")
    if outcome == "feasible_not_proven" and not (objective is not None and bound is not None and bound <= objective):
        problems.append("giltig men ej bevisad kräver gräns <= mål")
    if outcome in ("infeasible", "no_feasibility_conclusion") and (objective is not None or costs is not None):
        problems.append("lösning saknas men mål eller kostnad redovisas")
    if outcome not in ("optimal", "feasible_not_proven", "infeasible", "no_feasibility_conclusion"):
        problems.append(f"okänt utfall {outcome!r}")
    return rule("solver_report_consistent", TECHNICAL, FAIL if problems else PASS,
                "Solverns rapport är internt motsägelsefull." if problems
                else f"Solverns rapport (`{outcome}`) är internt konsekvent. Valideraren har inte bevisat optimalitet eller ogenomförbarhet.",
                problems, "konsistens: återgiven solverstatus")
