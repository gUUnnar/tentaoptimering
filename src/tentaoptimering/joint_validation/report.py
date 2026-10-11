"""Rule results and the three separate verdicts of the independent post-validation.

The validation answers three different questions and never merges them:

* solver: what the solver reported (not proven by this validator);
* technical: is the saved placement correct under the rules and values of the saved input;
* business: which rules rest on verified evidence, and which on assumptions or missing support.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PASS = "pass"
FAIL = "fail"
NOT_EVALUATED = "not_evaluated"
NOT_APPLICABLE = "not_applicable"
STATUSES = (PASS, FAIL, NOT_EVALUATED, NOT_APPLICABLE)

TECHNICAL = "technical"
BUSINESS = "business"
PROVENANCE = "provenance"

_MAX_OBJECTS = 20


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    axis: str
    status: str
    reason: str
    objects: tuple[str, ...] = ()
    object_count: int = 0
    rule_reference: str = ""


def rule(
    rule_id: str, axis: str, status: str, reason: str,
    objects: list[str] | tuple[str, ...] = (), reference: str = "",
) -> RuleResult:
    """Build a rule result; long object lists are truncated but the real count is kept."""
    ordered = tuple(sorted(set(str(item) for item in objects)))
    return RuleResult(rule_id, axis, status, reason, ordered[:_MAX_OBJECTS], len(ordered), reference)


def axis_status(rules: list[RuleResult], axis: str) -> str:
    """fail beats not_evaluated beats pass; an axis with only not_applicable rules is not_applicable."""
    statuses = [item.status for item in rules if item.axis == axis]
    if FAIL in statuses:
        return FAIL
    if NOT_EVALUATED in statuses:
        return NOT_EVALUATED
    if PASS in statuses:
        return PASS
    return NOT_APPLICABLE


def summarize(rules: list[RuleResult], solver_outcome: str | None) -> dict[str, Any]:
    technical = axis_status(rules, TECHNICAL)
    business = axis_status(rules, BUSINESS)
    provenance = axis_status(rules, PROVENANCE)
    return {
        "solver_status": {
            "reported_outcome": solver_outcome,
            "note": "Återgiven från solverresultatet. Valideraren bevisar varken optimalitet eller ogenomförbarhet.",
        },
        "technical_validation": technical,
        "business_verification": business,
        "provenance": provenance,
        "technically_validated": technical == PASS and provenance != FAIL,
        "counts": {status: sum(1 for item in rules if item.status == status) for status in STATUSES},
    }


def to_payload(rules: list[RuleResult], solver_outcome: str | None, run: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "joint-validation-v1",
        "run": run,
        "summary": summarize(rules, solver_outcome),
        "rules": [asdict(item) for item in rules],
    }


def markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# Oberoende eftervalidering: {payload['run'].get('problem_id')}", "",
        f"- Solverns status (återgiven, ej bevisad av valideraren): `{summary['solver_status']['reported_outcome']}`.",
        f"- Teknisk eftervalidering: `{summary['technical_validation']}`.",
        f"- Verksamhetsmässig verifiering: `{summary['business_verification']}`.",
        f"- Filernas ursprung och integritet: `{summary['provenance']}`.",
        f"- Tekniskt validerad: `{summary['technically_validated']}`.", "",
        "En tekniskt korrekt lösning är inte verksamhetsmässigt verifierad. Regler utan dataunderlag får aldrig `pass`.", "",
    ]
    for axis, title in ((TECHNICAL, "Teknisk eftervalidering"), (BUSINESS, "Verksamhetsmässig verifiering"),
                        (PROVENANCE, "Ursprung och integritet")):
        lines += [f"## {title}", "", "| Regel | Status | Orsak | Objekt |", "|---|---|---|---|"]
        for item in payload["rules"]:
            if item["axis"] != axis:
                continue
            shown = ", ".join(item["objects"]) + (f" (+{item['object_count'] - len(item['objects'])})"
                                                   if item["object_count"] > len(item["objects"]) else "")
            lines.append(f"| `{item['rule_id']}` | {item['status']} | {item['reason'].replace('|', '/')} | {shown} |")
        lines.append("")
    return "\n".join(lines)
