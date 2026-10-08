from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .canonical_demand import build_scope_report, provisional_scope_decisions
from .loaders import load_bookings, load_ladok, load_leases
from .linkage import candidate_linkage
from .model_inputs import (
    build_optimization_inputs,
    load_demand_measure,
    load_poc_policy,
    load_room_register,
)
from .normalize import normalize_bookings, normalize_ladok, normalize_leases
from .paths import REPO_ROOT, SourceFiles
from .provenance import write_run_manifest
from .reporting import (
    write_baseline_report,
    write_linkage_json,
    write_linkage_report,
    write_optimization_readiness_json,
    write_optimization_readiness_report,
    write_quality_json,
    write_scope_json,
    write_scope_report,
)
from .validation import validate_bookings, validate_ladok, validate_leases


@dataclass(frozen=True)
class PipelineOutputs:
    bookings_csv: Path
    ladok_csv: Path
    leases_csv: Path
    candidate_linkage_csv: Path
    exam_events_csv: Path
    activity_booking_candidates_csv: Path
    room_inventory_csv: Path
    optimization_rooms_csv: Path
    optimization_demands_csv: Path
    optimization_placements_csv: Path
    demand_scope_csv: Path
    baseline_report: Path
    quality_json: Path
    linkage_report: Path
    linkage_json: Path
    optimization_readiness_report: Path
    optimization_readiness_json: Path
    demand_scope_report: Path
    demand_scope_json: Path
    run_manifest_json: Path


def output_paths(processed_dir: Path, report_dir: Path) -> PipelineOutputs:
    return PipelineOutputs(
        bookings_csv=processed_dir / "bookings.csv",
        ladok_csv=processed_dir / "ladok_activities.csv",
        leases_csv=processed_dir / "lease_rows.csv",
        candidate_linkage_csv=processed_dir / "candidate_linkage.csv",
        exam_events_csv=processed_dir / "exam_events.csv",
        activity_booking_candidates_csv=processed_dir / "activity_booking_candidates.csv",
        room_inventory_csv=processed_dir / "room_inventory.csv",
        optimization_rooms_csv=processed_dir / "optimization_rooms.csv",
        optimization_demands_csv=processed_dir / "optimization_demands.csv",
        optimization_placements_csv=processed_dir / "optimization_placements.csv",
        demand_scope_csv=processed_dir / "demand_scope.csv",
        baseline_report=report_dir / "baseline.md",
        quality_json=report_dir / "data_quality.json",
        linkage_report=report_dir / "candidate_linkage.md",
        linkage_json=report_dir / "candidate_linkage.json",
        optimization_readiness_report=report_dir / "optimization_readiness.md",
        optimization_readiness_json=report_dir / "optimization_readiness.json",
        demand_scope_report=report_dir / "demand_scope.md",
        demand_scope_json=report_dir / "demand_scope.json",
        run_manifest_json=report_dir / "run_manifest.json",
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def run_pipeline(source_dir: Path, processed_dir: Path, report_dir: Path) -> PipelineOutputs:
    sources = SourceFiles(source_dir=source_dir)
    sources.validate()

    bookings = normalize_bookings(load_bookings(sources.bookings))
    ladok = normalize_ladok(load_ladok(sources.ladok))
    leases = normalize_leases(load_leases(sources.leases))
    linkage = candidate_linkage(bookings, ladok)
    parameter_path = REPO_ROOT / "config" / "parameters.toml"
    demand_measure = load_demand_measure(parameter_path)
    poc_policy = load_poc_policy(parameter_path)
    official_rooms = load_room_register(REPO_ROOT / "config" / "room_register.toml")
    model_inputs = build_optimization_inputs(
        bookings, ladok, leases, demand_measure, official_rooms, poc_policy
    )
    scope_report = build_scope_report(
        ladok, provisional_scope_decisions(ladok, model_inputs.activity_booking_candidates)
    )

    outputs = output_paths(processed_dir, report_dir)
    _write_csv(bookings, outputs.bookings_csv)
    _write_csv(ladok, outputs.ladok_csv)
    _write_csv(leases, outputs.leases_csv)
    _write_csv(linkage.candidate_links, outputs.candidate_linkage_csv)
    _write_csv(model_inputs.exam_events, outputs.exam_events_csv)
    _write_csv(model_inputs.activity_booking_candidates, outputs.activity_booking_candidates_csv)
    _write_csv(model_inputs.room_inventory, outputs.room_inventory_csv)
    _write_csv(model_inputs.optimization_rooms, outputs.optimization_rooms_csv)
    _write_csv(model_inputs.optimization_demands, outputs.optimization_demands_csv)
    _write_csv(model_inputs.optimization_placements, outputs.optimization_placements_csv)
    _write_csv(scope_report.activities, outputs.demand_scope_csv)

    results = {
        "Bokningsplaceringar": validate_bookings(bookings),
        "Ladok-aktiviteter": validate_ladok(ladok),
        "Lokal- och kostnadsrader": validate_leases(leases),
    }
    write_baseline_report(results, outputs.baseline_report)
    write_quality_json(results, outputs.quality_json)
    write_linkage_report(linkage, outputs.linkage_report)
    write_linkage_json(linkage, outputs.linkage_json)
    write_optimization_readiness_report(model_inputs, outputs.optimization_readiness_report)
    write_optimization_readiness_json(model_inputs, outputs.optimization_readiness_json)
    write_scope_report(scope_report, outputs.demand_scope_report)
    write_scope_json(scope_report, outputs.demand_scope_json)
    write_run_manifest(
        sources,
        {
            "parameters": REPO_ROOT / "config" / "parameters.toml",
            "room_register": REPO_ROOT / "config" / "room_register.toml",
        },
        {
            "bookings": (outputs.bookings_csv, bookings),
            "ladok_activities": (outputs.ladok_csv, ladok),
            "lease_rows": (outputs.leases_csv, leases),
            "candidate_linkage": (outputs.candidate_linkage_csv, linkage.candidate_links),
            "exam_events": (outputs.exam_events_csv, model_inputs.exam_events),
            "activity_booking_candidates": (
                outputs.activity_booking_candidates_csv,
                model_inputs.activity_booking_candidates,
            ),
            "room_inventory": (outputs.room_inventory_csv, model_inputs.room_inventory),
            "optimization_rooms": (
                outputs.optimization_rooms_csv,
                model_inputs.optimization_rooms,
            ),
            "optimization_demands": (
                outputs.optimization_demands_csv,
                model_inputs.optimization_demands,
            ),
            "optimization_placements": (
                outputs.optimization_placements_csv,
                model_inputs.optimization_placements,
            ),
            "demand_scope": (outputs.demand_scope_csv, scope_report.activities),
        },
        outputs.run_manifest_json,
    )
    return outputs
