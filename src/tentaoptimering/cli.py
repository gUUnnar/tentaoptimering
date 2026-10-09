from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
import sys
import tomllib
from typing import Any

from .optimization_runs import compare_runs, load_run_result, run_optimization
from .integrated_runs import run_integrated_term
from .integrated_validation import write_validation_report
from .joint_inputs import run_real_subset
from .joint_validation import write_validation
from .optimizer_config import load_scenario_config
from .parameter_catalog import load_parameter_catalog
from .paths import REPO_ROOT, default_source_dir
from .pipeline import PipelineOutputs, output_paths, run_pipeline


SCHEMA_VERSION = 1
DEFAULT_RUNS_DIR = REPO_ROOT / "runs"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Förbered och inspektera lokala, maskinläsbara optimeringsunderlag."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=(
            "prepare",
            "status",
            "resources",
            "parameters",
            "joint-parameters",
            "validate-config",
            "optimize",
            "result",
            "compare",
            "optimize-term",
            "optimize-joint",
            "validate-joint-run",
            "validate-term-run",
        ),
        default="prepare",
        help="prepare bygger om underlaget; status läser senast genererade resultat.",
    )
    parser.add_argument("--source-dir", type=Path, default=default_source_dir())
    parser.add_argument("--processed-dir", type=Path, default=REPO_ROOT / "data" / "processed")
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--run-ids", nargs="+")
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        dest="output_format",
        help="Utdataformat. JSON är standard för verktygsintegration.",
    )
    return parser


def _output_map(outputs: PipelineOutputs) -> dict[str, str]:
    return {
        item.name: str(getattr(outputs, item.name).resolve())
        for item in fields(PipelineOutputs)
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Resultatfilen saknas: {path}. Kör kommandot 'prepare' först."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _warnings(metrics: dict[str, Any]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if metrics.get("rooms_with_verified_capacity", 0) == 0:
        poc_enabled = metrics.get("poc_policy_allows_current_published_capacity") is True
        warnings.append(
            {
                "code": (
                    "UNVERIFIED_ROOM_CAPACITY_POC_ONLY"
                    if poc_enabled
                    else "ROOM_CAPACITY_MISSING"
                ),
                "message": (
                    "Publicerad kapacitet används endast för explorativ PoC; den är inte "
                    "verifierad för operativ schemaläggning."
                    if poc_enabled
                    else "Ingen sal har verifierad kapacitet; kapacitetsoptimering är blockerad."
                ),
            }
        )
    if metrics.get("operational_scheduling_readiness") == (
        "blocked_missing_verified_availability_and_business_rules"
    ):
        warnings.append(
            {
                "code": "OPERATIONAL_SCHEDULING_NOT_READY",
                "message": "PoC-underlaget saknar verifierad kalender och verksamhetsregler.",
            }
        )
    if metrics.get("ladok_activities_ambiguous_candidates", 0) > 0:
        warnings.append(
            {
                "code": "AMBIGUOUS_ACTIVITY_BOOKING_LINKS",
                "message": "Tvetydiga Ladok–bokningskandidater är separerade från underlaget.",
            }
        )
    if metrics.get("optimization_demands_missing_configured_value", 0) > 0:
        warnings.append(
            {
                "code": "DEMAND_VALUE_MISSING",
                "message": "Entydiga kandidater saknar det konfigurerade efterfrågevärdet.",
            }
        )
    reconciliation_gap = metrics.get("published_capacity_reconciliation_gap")
    if reconciliation_gap not in (None, 0):
        warnings.append(
            {
                "code": "PUBLISHED_CAPACITY_TOTAL_MISMATCH",
                "message": (
                    "Publicerad totalsumma stämmer inte med summan av individuella kapaciteter."
                ),
            }
        )
    return warnings


def _status_payload(command: str, outputs: PipelineOutputs) -> dict[str, Any]:
    readiness = _read_json(outputs.optimization_readiness_json)
    manifest = _read_json(outputs.run_manifest_json)
    metrics = readiness["metrics"]
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": "ok",
        "optimization_readiness": {
            "state": metrics["capacity_optimization_readiness"],
            "metrics": metrics,
        },
        "warnings": _warnings(metrics),
        "outputs": _output_map(outputs),
        "run_manifest": manifest,
    }


def _parameters_payload() -> dict[str, Any]:
    path = REPO_ROOT / "config" / "parameters.toml"
    parameters = tomllib.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "parameters",
        "status": "ok",
        "parameter_registry": str(path.resolve()),
        "parameters": parameters["parameter"],
    }


def _joint_parameters_payload() -> dict[str, Any]:
    path = REPO_ROOT / "config" / "joint_parameter_catalog.toml"
    catalog = load_parameter_catalog(path)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "joint-parameters",
        "status": "ok",
        "catalog_version": catalog.version,
        "parameter_catalog": str(path.resolve()),
        "parameters": [item.__dict__ for item in catalog.parameters],
    }


def _resources_payload(outputs: PipelineOutputs) -> dict[str, Any]:
    readiness = _read_json(outputs.optimization_readiness_json)
    manifest = _read_json(outputs.run_manifest_json)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "resources",
        "status": "ok",
        "readiness": readiness["metrics"],
        "resources": {
            "rooms": manifest["artifacts"]["optimization_rooms"],
            "demands": manifest["artifacts"]["optimization_demands"],
            "historical_placements": manifest["artifacts"]["optimization_placements"],
        },
        "outputs": _output_map(outputs),
    }


def _require(value: Any, option: str, command: str) -> Any:
    if value is None:
        raise ValueError(f"Kommandot '{command}' kräver {option}.")
    return value


def _command_payload(args: argparse.Namespace, outputs: PipelineOutputs) -> dict[str, Any]:
    if args.command == "prepare":
        outputs = run_pipeline(args.source_dir, args.processed_dir, args.report_dir)
        return _status_payload(args.command, outputs)
    if args.command == "status":
        return _status_payload(args.command, outputs)
    if args.command == "resources":
        return _resources_payload(outputs)
    if args.command == "parameters":
        return _parameters_payload()
    if args.command == "joint-parameters":
        return _joint_parameters_payload()
    if args.command == "validate-config":
        config_path = _require(args.config, "--config", args.command)
        config = load_scenario_config(config_path)
        return {
            "schema_version": SCHEMA_VERSION,
            "command": args.command,
            "status": "ok",
            "valid": True,
            "config": config.to_dict(),
        }
    if args.command == "optimize":
        config_path = _require(args.config, "--config", args.command)
        run = run_optimization(
            config_path, args.processed_dir, args.report_dir, args.runs_dir
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "command": args.command,
            "status": "ok",
            "run": run,
        }
    if args.command == "optimize-term":
        config_path = _require(args.config, "--config", args.command)
        return {
            "schema_version": SCHEMA_VERSION,
            "command": args.command,
            "status": "ok",
            "run": run_integrated_term(config_path, args.processed_dir, args.runs_dir),
        }
    if args.command == "optimize-joint":
        config_path = _require(args.config, "--config", args.command)
        run = run_real_subset(
            config_path,
            args.processed_dir,
            REPO_ROOT / "config" / "joint_parameter_catalog.toml",
            args.runs_dir,
        )
        failed = run["validation"]["technical_validation"] == "fail"
        return {
            "schema_version": SCHEMA_VERSION,
            "command": args.command,
            "status": "technical_validation_failed" if failed else "ok",
            "run": run,
        }
    if args.command == "validate-joint-run":
        run_id = _require(args.run_id, "--run-id", args.command)
        payload = write_validation(
            args.runs_dir / run_id,
            processed_dir=args.processed_dir,
            config_path=args.config,
            catalog_path=REPO_ROOT / "config" / "joint_parameter_catalog.toml",
            source_dir=args.source_dir,
            source_manifest=args.report_dir / "run_manifest.json",
        )
        failed = payload["summary"]["technical_validation"] == "fail" or payload["summary"]["provenance"] == "fail"
        return {
            "schema_version": SCHEMA_VERSION,
            "command": args.command,
            "status": "technical_validation_failed" if failed else "ok",
            "validation": payload,
        }
    if args.command == "validate-term-run":
        run_id = _require(args.run_id, "--run-id", args.command)
        return {
            "schema_version": SCHEMA_VERSION,
            "command": args.command,
            "status": "ok",
            "validation": write_validation_report(args.runs_dir / run_id),
        }
    if args.command == "result":
        run_id = _require(args.run_id, "--run-id", args.command)
        return {
            "schema_version": SCHEMA_VERSION,
            "command": args.command,
            "status": "ok",
            "run": load_run_result(args.runs_dir, run_id),
        }
    run_ids = _require(args.run_ids, "--run-ids", args.command)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": args.command,
        "status": "ok",
        "comparison": compare_runs(args.runs_dir, run_ids),
    }


def _emit(payload: dict[str, Any], output_format: str, stream: Any | None = None) -> None:
    stream = stream if stream is not None else sys.stdout
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2), file=stream)
        return
    if payload["status"] == "error":
        print(f"Fel: {payload['error']['message']}", file=stream)
        return
    if payload["command"] in {"optimize", "optimize-term", "optimize-joint"}:
        run = payload["run"]
        print(f"Körning: {run['run_id']}", file=stream)
        if payload["command"] == "optimize":
            print(f"Utfall: {run['outcome']}", file=stream)
            print(f"Solverstatus: {run['solver']['status']}", file=stream)
        elif payload["command"] == "optimize-term":
            print(f"Utfall: {run['result']['solution']['status']}", file=stream)
            print(f"Optimalitetsgap: {run['result']['solution']['optimality_gap']}", file=stream)
        else:
            print(f"Utfall: {run['result']['solver']['outcome']}", file=stream)
            print(f"Optimalitetsgap: {run['result']['solver']['relative_gap']}", file=stream)
        report_name = "joint_report.md" if payload["command"] == "optimize-joint" else "report.md"
        print(f"Rapport: {run['artifacts'][report_name]}", file=stream)
        if payload["command"] == "optimize-joint":
            _emit_joint_validation(run["validation"], stream)
        return
    if payload["command"] == "validate-joint-run":
        _emit_joint_validation(payload["validation"]["summary"], stream)
        print(f"Rapport: {Path(payload['validation']['run']['run_dir']) / 'joint_validation.md'}", file=stream)
        return
    if payload["command"] == "validate-term-run":
        validation = payload["validation"]
        print(f"Teknisk placering: {validation['report']['technical_placement_completeness']['status']}", file=stream)
        print(f"Verksamhetsmässig genomförbarhet: {validation['report']['business_feasibility']['status']}", file=stream)
        print(f"Rapport: {validation['artifacts']['validation.md']}", file=stream)
        return
    if payload["command"] not in {"prepare", "status"}:
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream)
        return
    readiness = payload["optimization_readiness"]
    print(f"Kommando: {payload['command']}", file=stream)
    print(f"Status: {readiness['state']}", file=stream)
    print("Resultatfiler:", file=stream)
    for name, path in payload["outputs"].items():
        print(f"- {name}: {path}", file=stream)


def _emit_joint_validation(summary: dict[str, Any], stream: Any) -> None:
    print(f"Solverns status (återgiven): {summary['solver_status']['reported_outcome']}", file=stream)
    print(f"Teknisk eftervalidering: {summary['technical_validation']}", file=stream)
    print(f"Verksamhetsmässig verifiering: {summary['business_verification']}", file=stream)
    print(f"Ursprung och integritet: {summary['provenance']}", file=stream)


def _error_payload(command: str, error: Exception) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": "error",
        "error": {"type": type(error).__name__, "message": str(error)},
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = output_paths(args.processed_dir, args.report_dir)
    try:
        payload = _command_payload(args, outputs)
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as error:
        _emit(_error_payload(args.command, error), args.output_format, sys.stderr)
        return 2
    except Exception as error:  # Tool callers must still receive structured failure details.
        _emit(_error_payload(args.command, error), args.output_format, sys.stderr)
        return 1
    _emit(payload, args.output_format)
    return 3 if payload.get("status") == "technical_validation_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
