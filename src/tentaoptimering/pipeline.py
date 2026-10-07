from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .loaders import load_bookings, load_ladok, load_leases
from .normalize import normalize_bookings, normalize_ladok, normalize_leases
from .paths import SourceFiles
from .reporting import write_baseline_report, write_quality_json
from .validation import validate_bookings, validate_ladok, validate_leases


@dataclass(frozen=True)
class PipelineOutputs:
    bookings_csv: Path
    ladok_csv: Path
    leases_csv: Path
    baseline_report: Path
    quality_json: Path


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def run_pipeline(source_dir: Path, processed_dir: Path, report_dir: Path) -> PipelineOutputs:
    sources = SourceFiles(source_dir=source_dir)
    sources.validate()

    bookings = normalize_bookings(load_bookings(sources.bookings))
    ladok = normalize_ladok(load_ladok(sources.ladok))
    leases = normalize_leases(load_leases(sources.leases))

    outputs = PipelineOutputs(
        bookings_csv=processed_dir / "bookings.csv",
        ladok_csv=processed_dir / "ladok_activities.csv",
        leases_csv=processed_dir / "lease_rows.csv",
        baseline_report=report_dir / "baseline.md",
        quality_json=report_dir / "data_quality.json",
    )
    _write_csv(bookings, outputs.bookings_csv)
    _write_csv(ladok, outputs.ladok_csv)
    _write_csv(leases, outputs.leases_csv)

    results = {
        "Bokningsplaceringar": validate_bookings(bookings),
        "Ladok-aktiviteter": validate_ladok(ladok),
        "Lokal- och kostnadsrader": validate_leases(leases),
    }
    write_baseline_report(results, outputs.baseline_report)
    write_quality_json(results, outputs.quality_json)
    return outputs
