"""Validate a saved joint-optimization run without re-running the optimizer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .context import MalformedArtifact, build_context
from .integrity import MANIFEST_FILE, integrity_rules, load_artifacts
from .report import FAIL, NOT_EVALUATED, TECHNICAL, RuleResult, markdown, rule, to_payload
from .rules_business import business_rules
from .rules_placement import calendar_rules, demand_rules
from .rules_rooms import room_rules
from .rules_staffing_cost import staffing_cost_rules

VALIDATION_JSON = "joint_validation.json"
VALIDATION_MD = "joint_validation.md"


def validate_run(
    run_dir: Path,
    processed_dir: Path | None = None,
    config_path: Path | None = None,
    catalog_path: Path | None = None,
    source_dir: Path | None = None,
    source_manifest: Path | None = None,
) -> dict[str, Any]:
    """Return the machine-readable validation of a saved run. Writes nothing."""
    run_dir = Path(run_dir)
    problem, result, manifest, rules = load_artifacts(run_dir)
    if problem is None or result is None:
        return to_payload(rules, None, {"run_dir": str(run_dir), "problem_id": None})
    if manifest is not None:
        rules += integrity_rules(run_dir, problem, result, manifest, processed_dir, config_path, catalog_path, source_dir, source_manifest)
    else:
        rules.append(rule("manifest_hashes", "provenance", NOT_EVALUATED, f"{MANIFEST_FILE} saknas; filernas integritet kan inte kontrolleras."))
    solver = result.get("solver")
    outcome = solver.get("outcome") if isinstance(solver, dict) else None
    try:
        context = build_context(problem, result)
    except MalformedArtifact as error:
        rules.append(rule("input_wellformed", TECHNICAL, FAIL, f"Indata eller resultat är felaktigt format: {error}.", reference="krav: giltigt kontrakt"))
        return to_payload(rules, outcome, {"run_dir": str(run_dir), "problem_id": problem.get("problem_id")})
    rules.append(rule("input_wellformed", TECHNICAL, "pass", "Indata och resultat kan läsas enligt kontraktet.", reference="krav: giltigt kontrakt"))
    for group in (demand_rules, calendar_rules, room_rules, staffing_cost_rules, business_rules):
        rules += _guarded(group, context)
    return to_payload(rules, outcome, {"run_dir": str(run_dir), "problem_id": problem.get("problem_id")})


def _guarded(group: Any, context: Any) -> list[RuleResult]:
    """A rule group that cannot run on a malformed artifact is reported, never raised."""
    try:
        return group(context)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as error:
        return [rule(f"{group.__name__}_error", TECHNICAL, FAIL,
                     f"Regelgruppen kunde inte prövas; artefakten är sannolikt felformad ({type(error).__name__}: {error}).",
                     reference="krav: giltigt kontrakt")]


def write_validation(run_dir: Path, **kwargs: Any) -> dict[str, Any]:
    """Validate and save joint_validation.json and joint_validation.md next to the artifacts.

    The solver input, result and manifest are never modified.
    """
    payload = validate_run(run_dir, **kwargs)
    run_dir = Path(run_dir)
    (run_dir / VALIDATION_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / VALIDATION_MD).write_text(markdown(payload), encoding="utf-8")
    return payload


def failing_rules(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in payload["rules"] if item["status"] == FAIL]
