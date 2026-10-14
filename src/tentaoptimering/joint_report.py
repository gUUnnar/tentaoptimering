"""The text report of a saved joint run (`joint_report.md`): solver outcome, costs, verification status and limits."""

from __future__ import annotations

from typing import Any

from .joint_contract import JointOptimizationInput


def proof_lines(solver: Any) -> list[str]:
    """A solution without an optimality proof is never presented as the largest possible saving."""
    if solver.outcome != "feasible_not_proven" or solver.best_objective_bound_ore is None:
        return []
    return [
        f"- Kostnaden är en verifierad övre gräns, inte ett bevisat optimum: den lägsta möjliga kostnaden i modellen "
        f"ligger mellan {solver.best_objective_bound_ore} och {solver.objective_value_ore} öre. "
        "Besparingen får därför inte redovisas som bevisad maximal besparing.",
    ]


def validation_lines(summary: dict[str, Any]) -> list[str]:
    """Report the three verdicts separately; the solver result itself is never altered."""
    return [
        "", "## Oberoende eftervalidering (joint_validation.md)", "",
        f"- Solverns status (återgiven, ej bevisad av valideraren): `{summary['solver_status']['reported_outcome']}`.",
        f"- Teknisk eftervalidering: `{summary['technical_validation']}`.",
        f"- Verksamhetsmässig verifiering: `{summary['business_verification']}`.",
        f"- Filernas ursprung och integritet: `{summary['provenance']}`.",
        f"- Tekniskt validerad: `{summary['technically_validated']}`.", "",
    ]


def build_report(problem: JointOptimizationInput, result: Any) -> str:
    solver = result.solver
    costs = result.costs
    return "\n".join([
        f"# Gemensam verklig delmängd: {problem.problem_id}", "",
        f"- Solverutfall: `{solver.outcome}` (`{solver.raw_status}`), strategi `{solver.strategy}`.",
        f"- Beräkningstid: {solver.wall_time_seconds:.3f} sekunder.",
        f"- Funnet jämförbart kostnadsmål: {solver.objective_value_ore} öre.",
        f"- Bästa kostnadsgräns: {solver.best_objective_bound_ore} öre.",
        f"- Relativt gap: {solver.relative_gap}.",
        *proof_lines(solver),
        f"- Teknisk placeringsfullständighet: {result.coverage.technical_placement_complete}.",
        f"- Behov/deltagare: {result.coverage.exam_demands_scheduled}/{result.coverage.exam_demands_total}, {result.coverage.participants_total} deltagare.",
        f"- Bemanningspool: {result.staff_pool_size} anonyma samtidiga resurser.",
        f"- Ändrade tentamenstillfällen: {result.changed_exam_demands}.", "",
        "## Verifieringsstatus", "",
        *[f"- {key}: {value}" for key, value in (result.verification or {}).items()], "",
        "## Kostnadskomponenter", "",
        f"- Långsiktiga salar: {costs.annual_room_cost_ore if costs else None} öre.",
        f"- Externa salstillfällen: {costs.external_room_session_cost_ore if costs else None} öre.",
        f"- Årlig bemanningspool: {costs.annual_staff_pool_cost_ore if costs else None} öre.",
        f"- Rörlig salstillfällesbemanning: {costs.staff_session_cost_ore if costs else None} öre.", "",
        "## Datatäckning och begränsningar", "",
        f"- Modellerade tentamensbehov: {problem.scope.modeled_exam_demands} av en uttryckligen vald delmängd.",
        f"- Hela källpopulationen: {problem.scope.source_activities_total} aktiviteter, varav {problem.scope.unresolved_source_activities} oavgjorda.",
        *[f"- {item}" for item in result.limitations], "",
    ])
