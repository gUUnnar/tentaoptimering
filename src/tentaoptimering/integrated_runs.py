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
from .integrated_inputs import load_term_model_inputs
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
    _write_csv(run_dir / "demand_traceability.csv", inputs.demand_traceability)
    payload = _payload(run_id, scenario, inputs.scope_metrics, result)
    (run_dir / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "report.md").write_text(_report(payload), encoding="utf-8")
    return {"run_id": run_id, "result": payload, "artifacts": {name: str((run_dir / name).resolve()) for name in (
        "scenario.toml", "assignments.csv", "room_sessions.csv", "demand_traceability.csv", "result.json", "report.md",
    )}}


def _write_csv(path: Path, rows: tuple[dict[str, Any], ...]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _payload(run_id: str, scenario: Any, scope_metrics: dict[str, int], result: TermRunResult) -> dict[str, Any]:
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
            "anonymous_staff_pool_size": result.staff_pool_size,
            "rooms_used": used_rooms,
            "room_count": len(used_rooms),
            "assignment_rows": len(result.assignments),
            "room_sessions": len(result.room_sessions),
        },
        "model_completeness": result.model_completeness,
        "scope_metrics": scope_metrics,
        "limitations": [
            "Rumsinventariet saknar verifierad kalender och är endast ett explorativt scenario.",
            "Kostnaderna är ersättbara scenarioproxyer, inte realiserbar hyra eller avtalskostnad.",
            "Bemanningen är en anonym samtidighetspool; individuell schemaläggning, raster, restider och arbetstidsvillkor kontrolleras inte.",
            "Körningen är konstruktiv och bevisar inte global optimalitet; optimalitetsgap saknas därför.",
            "De oavgjorda källaktiviteterna ingår inte i efterfrågan och hindrar en fullständig beräkning för hela populationen.",
        ],
    }


def _report(payload: dict[str, Any]) -> str:
    solution = payload["solution"]
    completeness = payload["model_completeness"]
    return "\n".join([
        f"# Terminskörning: {payload['scenario']['scenario_id']}", "",
        "## Utfall", "",
        f"- Status: `{solution['status']}`.",
        f"- Beräkningstid: {solution['elapsed_seconds']:.3f} sekunder.",
        f"- Målfunktion: {solution['objective_ore']} öre per år enligt scenarioantagandena.",
        f"- Lokalportfölj: {solution['room_count']} rum ({', '.join(solution['rooms_used'])}).",
        f"- Anonym samtidig bemanningspool: {solution['anonymous_staff_pool_size']} resurser.",
        f"- Optimalitetsgap: `{solution['optimality_gap']}`.", "",
        "## Modellens fullständighet", "",
        f"- Täckning av inkluderade behov: {completeness['included_demand_coverage']:.1%} "
        f"({completeness['placed_exam_demands']} av {completeness['included_source_activities']}).",
        f"- Täckning av hela källpopulationen: {completeness['source_population_coverage']:.1%} "
        f"({completeness['included_source_activities']} av {completeness['source_activities_total']}).",
        f"- Oavgjorda källaktiviteter: {completeness['unresolved_source_activities']}.", "",
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
