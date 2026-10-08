from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import ortools
import pandas as pd

from .optimizer_config import ScenarioConfig, load_scenario_config
from .optimizer_model import OptimizationResult, solve_capacity_scenario
from .optimizer_validation import validate_solution


RUN_SCHEMA_VERSION = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Resultatfilen saknas: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-") or "scenario"


def _new_run_id(config: ScenarioConfig) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{_safe_id(config.scenario_id)}"


def _outcome(result: OptimizationResult) -> str:
    if result.solver_status == "optimal":
        if result.metrics["unplaced_exam_count"] == 0:
            return "complete_placement_optimal_for_weighted_objective"
        return "partial_placement_optimal_for_weighted_objective"
    if result.solver_status == "feasible":
        if result.metrics["unplaced_exam_count"] == 0:
            return "complete_placement_feasible_not_proven_optimal"
        return "partial_placement_feasible_not_proven_optimal"
    if result.solver_status == "infeasible":
        return "model_infeasible"
    if result.solver_status == "model_invalid":
        return "model_invalid"
    return "stopped_without_conclusive_solution"


def _input_manifest(
    config_path: Path,
    processed_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    source_manifest = _read_json(report_dir / "run_manifest.json")
    input_files = {
        "optimization_demands": processed_dir / "optimization_demands.csv",
        "optimization_rooms": processed_dir / "optimization_rooms.csv",
        "optimization_placements": processed_dir / "optimization_placements.csv",
    }
    return {
        "schema_version": 1,
        "scenario_config": {
            "filename": config_path.name,
            "sha256": _sha256(config_path),
        },
        "optimization_inputs": {
            name: {"filename": path.name, "sha256": _sha256(path)}
            for name, path in input_files.items()
        },
        "preparation_manifest": source_manifest,
    }


def _report_lines(payload: dict[str, Any]) -> list[str]:
    metrics = payload["metrics"]
    components = metrics["objective_components"]
    lines = [
        f"# Optimeringskörning {payload['run_id']}",
        "",
        f"Scenario: `{payload['scenario']['scenario_id']}`",
        "",
        f"Utfall: `{payload['outcome']}`",
        "",
        f"Solverstatus: `{payload['solver']['status']}`",
        "",
        "## Kapacitetsresultat",
        "",
        "| Mått | Värde |",
        "|---|---:|",
        f"| Tentamina i indata | {metrics['input_exam_count']} |",
        f"| Placerade tentamina | {metrics['placed_exam_count']} |",
        f"| Oplacerade tentamina | {metrics['unplaced_exam_count']} |",
        f"| Oplacerade deltagare | {metrics['unplaced_participants']} |",
        f"| Använda scenariorum | {metrics['rooms_used']} |",
        f"| Historisk topp i efterfrågan | {metrics['input_peak_concurrent_required_seats']} |",
        f"| Största aggregerade kapacitetsbrist | {metrics['maximum_aggregate_capacity_shortfall']} |",
        f"| Maximal samtidigt öppnad kapacitet | {metrics['max_simultaneous_open_capacity']} |",
        f"| Öppna salminuter | {components.get('room_open_minutes')} |",
        f"| Outnyttjade platsminuter | {components.get('unused_seat_minutes')} |",
        f"| Tidsflyttade tentamina | {components.get('rescheduled_exams')} |",
        "",
        f"Fullständig placering: `{metrics['full_placement_feasibility']}`",
        "",
        "## Solver",
        "",
        f"- Körtid: {payload['solver']['runtime_seconds']:.3f} sekunder",
        f"- Målfunktionsvärde: {payload['solver']['objective_value']}",
        f"- Bästa gräns: {payload['solver']['best_objective_bound']}",
        f"- Relativ optimalitetslucka: {payload['solver']['relative_gap']}",
        "",
        "## Eftervalidering",
        "",
        f"- Giltig: {payload['validation']['valid']}",
        f"- Kontroller: {', '.join(payload['validation']['checks'])}",
        "",
        "## Osäkerheter",
        "",
    ]
    lines.extend(f"- `{item['code']}`: {item['message']}" for item in payload["warnings"])
    lines.extend(
        [
            "",
            "Resultatet visar teoretiskt kapacitetsutnyttjande under scenarioantagandena.",
            "Det är inte ett kalenderverifierat tentamensschema eller en beräknad besparing.",
            "",
        ]
    )
    return lines


def run_optimization(
    config_path: Path,
    processed_dir: Path,
    report_dir: Path,
    runs_dir: Path,
) -> dict[str, Any]:
    config = load_scenario_config(config_path)
    manifest = _input_manifest(config_path, processed_dir, report_dir)
    demands = pd.read_csv(processed_dir / "optimization_demands.csv", encoding="utf-8-sig")
    rooms = pd.read_csv(processed_dir / "optimization_rooms.csv", encoding="utf-8-sig")
    placements = pd.read_csv(
        processed_dir / "optimization_placements.csv", encoding="utf-8-sig"
    )
    result = solve_capacity_scenario(demands, rooms, placements, config)
    validation = validate_solution(
        demands, rooms, result.assignments, result.unplaced, config
    )
    run_id = _new_run_id(config)
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    assignments_path = run_dir / "assignments.csv"
    unplaced_path = run_dir / "unplaced.csv"
    result.assignments.to_csv(assignments_path, index=False, encoding="utf-8-sig")
    result.unplaced.to_csv(unplaced_path, index=False, encoding="utf-8-sig")
    (run_dir / "scenario.toml").write_text(
        config_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    _write_json(run_dir / "input_manifest.json", manifest)
    payload = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "outcome": _outcome(result),
        "scenario": config.to_dict(),
        "solver": {
            "engine": "OR-Tools CP-SAT",
            "ortools_version": ortools.__version__,
            "status": result.solver_status,
            "status_code": result.solver_status_code,
            "runtime_seconds": result.runtime_seconds,
            "objective_value": result.objective_value,
            "best_objective_bound": result.best_objective_bound,
            "relative_gap": result.relative_gap,
            "statistics": result.solver_statistics,
        },
        "metrics": result.metrics,
        "validation": validation,
        "warnings": result.warnings,
        "artifacts": {
            "run_directory": str(run_dir.resolve()),
            "scenario_config": str((run_dir / "scenario.toml").resolve()),
            "input_manifest": str((run_dir / "input_manifest.json").resolve()),
            "assignments": str(assignments_path.resolve()),
            "unplaced": str(unplaced_path.resolve()),
            "report": str((run_dir / "report.md").resolve()),
            "result": str((run_dir / "result.json").resolve()),
        },
    }
    _write_json(run_dir / "result.json", payload)
    (run_dir / "report.md").write_text("\n".join(_report_lines(payload)), encoding="utf-8")
    return payload


def load_run_result(runs_dir: Path, run_id: str) -> dict[str, Any]:
    return _read_json(runs_dir / run_id / "result.json")


def compare_runs(runs_dir: Path, run_ids: list[str]) -> dict[str, Any]:
    if len(run_ids) < 2:
        raise ValueError("Minst två run-id krävs för en jämförelse.")
    results = [load_run_result(runs_dir, run_id) for run_id in run_ids]
    metric_names = (
        "placed_exam_count",
        "unplaced_exam_count",
        "unplaced_participants",
        "rooms_used",
        "max_simultaneous_open_capacity",
    )
    component_names = (
        "room_open_minutes",
        "unused_seat_minutes",
        "rescheduled_exams",
        "room_reassignments",
    )
    rows: list[dict[str, Any]] = []
    baseline = results[0]
    for result in results:
        metrics = result["metrics"]
        values = {name: metrics[name] for name in metric_names}
        values.update(
            {name: metrics["objective_components"][name] for name in component_names}
        )
        baseline_values = {name: baseline["metrics"][name] for name in metric_names}
        baseline_values.update(
            {
                name: baseline["metrics"]["objective_components"][name]
                for name in component_names
            }
        )
        rows.append(
            {
                "run_id": result["run_id"],
                "scenario_id": result["scenario"]["scenario_id"],
                "solver_status": result["solver"]["status"],
                "values": values,
                "delta_from_first": {
                    name: values[name] - baseline_values[name]
                    if values[name] is not None and baseline_values[name] is not None
                    else None
                    for name in values
                },
            }
        )
    comparison_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    comparison_dir = runs_dir / "comparisons"
    payload = {
        "schema_version": 1,
        "comparison_id": comparison_id,
        "baseline_run_id": run_ids[0],
        "runs": rows,
    }
    json_path = comparison_dir / f"{comparison_id}.json"
    report_path = comparison_dir / f"{comparison_id}.md"
    _write_json(json_path, payload)
    report_lines = [
        f"# Jämförelse {comparison_id}",
        "",
        f"Baslinje: `{run_ids[0]}`",
        "",
        "| Scenario | Status | Oplacerade tentamina | Oplacerade deltagare | Rum | Öppna salminuter | Tidsflyttade |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        values = row["values"]
        report_lines.append(
            f"| {row['scenario_id']} | {row['solver_status']} | "
            f"{values['unplaced_exam_count']} | {values['unplaced_participants']} | "
            f"{values['rooms_used']} | {values['room_open_minutes']} | "
            f"{values['rescheduled_exams']} |"
        )
    report_lines.extend(
        [
            "",
            "Jämförelsen avser scenarier under provisoriska kapacitets- och tillgänglighetsantaganden.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    payload["artifacts"] = {
        "json": str(json_path.resolve()),
        "report": str(report_path.resolve()),
    }
    _write_json(json_path, payload)
    return payload
