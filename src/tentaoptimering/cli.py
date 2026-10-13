from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
import sys
import threading
from typing import Any, Callable

from .joint_inputs import run_real_subset
from .joint_strategy.resources import CancelToken, ExecutionBudget
from .joint_validation import write_validation
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
            "joint-parameters",
            "optimize-joint",
            "validate-joint-run",
        ),
        default="prepare",
        help="prepare bygger om underlaget; status och resources läser senast genererade resultat; joint-parameters listar "
        "parameterkatalogen; optimize-joint kör den gemensamma optimeringen; validate-joint-run eftervaliderar en sparad körning.",
    )
    parser.add_argument("--source-dir", type=Path, default=default_source_dir())
    parser.add_argument("--processed-dir", type=Path, default=REPO_ROOT / "data" / "processed")
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--warm-start",
        default="auto",
        metavar="auto|none|RUN_ID",
        help="optimize-joint: starta från en tidigare sparad körning. auto väljer den senaste användbara körningen av "
        "samma problem; none stänger av; RUN_ID pekar ut en körning. Placeringen kontrolleras alltid mot de nya reglerna.",
    )
    parser.add_argument("--threads", type=int, default=0, help="optimize-joint: gemensam trådbudget för CP-SAT (0 = scenariots solver.workers).")
    parser.add_argument("--memory-mb", type=int, default=None, help="optimize-joint: minnesbudget för parallella dagkontroller (standard: hälften av ledigt minne).")
    parser.add_argument("--sequential-day-checks", action="store_true", help="optimize-joint: kör dagkontrollerna i tur och ordning.")
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


def _interruptible(action: Callable[[CancelToken], Any]) -> Any:
    """Run `action` so that the first Ctrl+C stops the solver and saves the best verified result so far.

    A second Ctrl+C is not caught. The solve runs in a thread because a native CP-SAT call in the main
    thread would postpone the interrupt until it returned.
    """
    cancel = CancelToken()
    outcome: dict[str, Any] = {}

    def work() -> None:
        try:
            outcome["value"] = action(cancel)
        except BaseException as error:  # handed to the calling thread
            outcome["error"] = error

    worker = threading.Thread(target=work, name="optimize-joint")
    worker.start()
    try:
        while worker.is_alive():
            worker.join(0.2)
    except KeyboardInterrupt:
        cancel.cancel()
        print("Avbryter: sparar bästa verifierade lösning hittills. Ctrl+C igen avbryter utan att spara.", file=sys.stderr)
        worker.join()
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


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
    if args.command == "joint-parameters":
        return _joint_parameters_payload()
    if args.command == "optimize-joint":
        config_path = _require(args.config, "--config", args.command)
        run = _interruptible(lambda cancel: run_real_subset(
            config_path,
            args.processed_dir,
            REPO_ROOT / "config" / "joint_parameter_catalog.toml",
            args.runs_dir,
            warm_start=args.warm_start,
            budget=ExecutionBudget(args.threads, args.memory_mb, not args.sequential_day_checks),
            cancel=cancel,
        ))
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
    raise ValueError(f"Okänt kommando: {args.command}")


def _emit(payload: dict[str, Any], output_format: str, stream: Any | None = None) -> None:
    stream = stream if stream is not None else sys.stdout
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2), file=stream)
        return
    if payload["status"] == "error":
        print(f"Fel: {payload['error']['message']}", file=stream)
        return
    if payload["command"] == "optimize-joint":
        run = payload["run"]
        print(f"Körning: {run['run_id']}", file=stream)
        print(f"Utfall: {run['result']['solver']['outcome']}", file=stream)
        print(f"Optimalitetsgap: {run['result']['solver']['relative_gap']}", file=stream)
        print(f"Rapport: {run['artifacts']['joint_report.md']}", file=stream)
        print(f"Varmstart: {run['warm_start']['decision']} – {run['warm_start']['explanation']}", file=stream)
        _emit_joint_validation(run["validation"], stream)
        return
    if payload["command"] == "validate-joint-run":
        _emit_joint_validation(payload["validation"]["summary"], stream)
        print(f"Rapport: {Path(payload['validation']['run']['run_dir']) / 'joint_validation.md'}", file=stream)
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
