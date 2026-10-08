from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .paths import SourceFiles


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_run_manifest(
    sources: SourceFiles,
    configuration_paths: dict[str, Path],
    artifacts: dict[str, tuple[Path, pd.DataFrame]],
    path: Path,
) -> None:
    """Write deterministic provenance for inputs, configuration and CSV outputs."""
    source_paths = {
        "bookings": sources.bookings,
        "ladok": sources.ladok,
        "leases": sources.leases,
    }
    payload = {
        "schema_version": 1,
        "sources": {
            name: {
                "filename": source_path.name,
                "bytes": source_path.stat().st_size,
                "sha256": sha256_file(source_path),
            }
            for name, source_path in source_paths.items()
        },
        "configuration": {
            name: {
                "filename": configuration_path.name,
                "sha256": sha256_file(configuration_path),
            }
            for name, configuration_path in configuration_paths.items()
        },
        "artifacts": {
            name: {
                "filename": artifact_path.name,
                "rows": int(len(frame)),
                "sha256": sha256_file(artifact_path),
            }
            for name, (artifact_path, frame) in artifacts.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
