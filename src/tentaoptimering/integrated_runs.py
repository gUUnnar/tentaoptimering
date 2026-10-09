"""Artifacts for reproducible exploratory whole-term runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

import pandas as pd

from .integrated_config import load_integrated_term_scenario
from .cost_comparison import preliminary_cost_comparison
from .integrated_inputs import load_term_model_inputs
from .run_integrity import write_run_integrity_manifest
from .term_run import TermRunResult, run_first_term_schedule


def run_integrated_term(config_path: Path, processed_dir: Path, runs_dir: Path) -> dict[str, Any]:
    """Run an assumption-based exploratory term schedule and persist auditable output."""
    scenario = load_integrated_term_scenario(config_path)
    inputs = load_term_model_inputs(processed_dir, scenario)
    result = run_first_term_schedule(inputs, scenario)
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{scenario.scenario_id}"
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(config_path, run_dir / "scenario.toml")
    _write_csv(run_dir / "assignments.csv", result.assignments)
    _write_csv(run_dir / "room_sessions.csv", result.room_sessions)
    _write_csv(run_dir / "staff_assignments.csv", result.staff_assignments)
    _write_csv(run_dir / "demand_traceability.csv", inputs.demand_traceability)
    (run_dir / "model_inputs.json").write_text(
        json.dumps({
            "demands": [
                _demand_input(item)
                for item in inputs.demands
            ],
            "rooms": [_room_input(item) for item in inputs.rooms],
            "demand_traceability": list(inputs.demand_traceability),
            "scope_metrics": inputs.scope_metrics,
            "scope_decisions": list(inputs.scope_decisions),
        }, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    payload = _payload(run_id, scenario, inputs.scope_metrics, result, preliminary_cost_comparison(processed_dir, result.objective_ore))
    (run_dir / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "report.md").write_text(_report(payload), encoding="utf-8")
    integrity_path = write_run_integrity_manifest(
        run_dir, "exploratory_constructive_term_v1"
    )
    return {"run_id": run_id, "result": payload, "artifacts": {name: str((run_dir / name).resolve()) for name in (
        "scenario.toml", "assignments.csv", "room_sessions.csv", "staff_assignments.csv", "demand_traceability.csv", "model_inputs.json", "result.json", "report.md", integrity_path.name,
    )}}


def _write_csv(path: Path, rows: tuple[dict[str, Any], ...]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _demand_input(item: Any) -> dict[str, Any]:
    data = asdict(item)
    data["allowed_pass_ids"] = sorted(item.allowed_pass_ids) if item.allowed_pass_ids else None
    data["program_ids"] = sorted(item.program_ids)
    return data


def _room_input(item: Any) -> dict[str, Any]:
    data = asdict(item)
    data["digital_capabilities"] = sorted(item.digital_capabilities)
    data["available_slot_ids"] = sorted(item.available_slot_ids) if item.available_slot_ids is not None else None
    return data


def _payload(run_id: str, scenario: Any, scope_metrics: dict[str, int], result: TermRunResult, cost_comparison: dict[str, object]) -> dict[str, Any]:
    used_rooms = sorted({row["room_id"] for row in result.assignments})
    return {
        "run_id": run_id,
        "scenario": {
            "scenario_id": scenario.scenario_id,
            "description": scenario.description,
            "assumptions": [asdict(item) for item in scenario.assumptions],
        },
        "method": result.method,
        "solution": {
            "status": result.status,
            "elapsed_seconds": result.elapsed_seconds,
            "optimality_gap": result.optimality_gap,
            "objective_ore": result.objective_ore,
            "annual_room_cost_ore": result.annual_room_cost_ore,
            "annual_staff_cost_ore": result.annual_staff_cost_ore,
            "annual_travel_cost_ore": result.annual_travel_cost_ore,
            "anonymous_staff_pool_size": result.staff_pool_size,
            "staff_work_minutes": result.staff_work_minutes,
            "staff_travel_minutes": result.staff_travel_minutes,
            "staff_idle_minutes": result.staff_idle_minutes,
            "rooms_used": used_rooms,
            "room_count": len(used_rooms),
            "assignment_rows": len(result.assignments),
            "room_sessions": len(result.room_sessions),
        },
        "model_completeness": result.model_completeness,
        "scope_metrics": scope_metrics,
        "cost_comparison": cost_comparison,
        "limitations": [
            "Rumsinventariet saknar verifierad kalender och är endast ett explorativt scenario.",
            "Kostnaderna är ersättbara scenarioproxyer, inte realiserbar hyra eller avtalskostnad.",
            "Bemanningen är anonymiserad men varje sparad vaktuppgift kontrolleras mot scenarioinställda pass, raster, vila och byggnadsbyte; regel- och kostnadsdata är fortfarande antaganden.",
            "Körningen är konstruktiv och bevisar inte global optimalitet; optimalitetsgap saknas därför.",
            "De oavgjorda källaktiviteterna ingår inte i efterfrågan och hindrar en fullständig beräkning för hela populationen.",
        ],
    }


def _report(payload: dict[str, Any]) -> str:
    solution = payload["solution"]
    completeness = payload["model_completeness"]
    comparison = payload["cost_comparison"]
    return "\n".join([
        f"# Terminskörning: {payload['scenario']['scenario_id']}", "",
        "## Utfall", "",
        f"- Status: `{solution['status']}`.",
        f"- Beräkningstid: {solution['elapsed_seconds']:.3f} sekunder.",
        f"- Målfunktion: {solution['objective_ore']} öre per år enligt scenarioantagandena.",
        f"- Lokalportfölj: {solution['room_count']} rum ({', '.join(solution['rooms_used'])}).",
        f"- Anonym samtidig bemanningspool: {solution['anonymous_staff_pool_size']} resurser.",
        f"- Beräknad vaktarbete/restid/bomtid: {solution['staff_work_minutes']}/{solution['staff_travel_minutes']}/{solution['staff_idle_minutes']} minuter.",
        f"- Optimalitetsgap: `{solution['optimality_gap']}`.", "",
        "## Modellens fullständighet", "",
        f"- Täckning av inkluderade behov: {completeness['included_demand_coverage']:.1%} "
        f"({completeness['placed_exam_demands']} av {completeness['included_source_activities']}).",
        f"- Täckning av hela källpopulationen: {completeness['source_population_coverage']:.1%} "
        f"({completeness['included_source_activities']} av {completeness['source_activities_total']}).",
        f"- Oavgjorda källaktiviteter: {completeness['unresolved_source_activities']}.", "",
        "## Kostnadsjämförelse", "",
        f"- Status: `{comparison['status']}`.",
        f"- Källans preliminära internhyreprofil: {comparison['source_baseline_preliminary_internal_rent_ore']} öre per år.",
        f"- Scenariots antagandekostnad: {comparison['scenario_assumption_cost_ore']} öre per år.",
        "- Teoretisk potential och verifierad realiserbar besparing: inte beräknade.", "",
        "## Begränsningar", "",
        *[f"- {item}" for item in payload["limitations"]], "",
        "## Antaganden", "",
        "| Id | Värde | Enhet | Källa | Status |",
        "| --- | --- | --- | --- | --- |",
        *[
            f"| {item['assumption_id']} | {item['value']} | {item['unit']} | {item['source']} | {item['status']} |"
            for item in payload["scenario"]["assumptions"]
        ], "",
    ])
