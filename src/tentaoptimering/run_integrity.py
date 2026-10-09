"""Integrity manifest for immutable inputs and outputs of a saved term run."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


MANIFEST_NAME = "run_integrity.json"
ARTIFACT_NAMES = (
    "scenario.toml",
    "model_inputs.json",
    "assignments.csv",
    "room_sessions.csv",
    "staff_assignments.csv",
    "demand_traceability.csv",
    "result.json",
)


@dataclass(frozen=True)
class IntegrityCheck:
    status: str
    reason: str
    object_ids: tuple[str, ...] = ()


def write_run_integrity_manifest(run_dir: Path, engine_id: str) -> Path:
    """Freeze exactly the files that define one completed term run."""
    hashes = {name: file_sha256(run_dir / name) for name in ARTIFACT_NAMES}
    payload = {
        "schema_version": 1,
        "engine_id": engine_id,
        "artifact_sha256": hashes,
        "frozen_spec_sha256": hashes["scenario.toml"],
        "model_inputs_sha256": hashes["model_inputs.json"],
    }
    path = run_dir / MANIFEST_NAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def verify_run_integrity(run_dir: Path) -> IntegrityCheck:
    """Reject changed saved artifacts; legacy runs without a manifest are not verified."""
    path = run_dir / MANIFEST_NAME
    if not path.is_file():
        return IntegrityCheck("not_evaluated", "Körningen saknar integritetsmanifest för frusen specifikation och modellindata.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return IntegrityCheck("fail", "Integritetsmanifestet är inte giltig JSON.", (MANIFEST_NAME,))
    hashes = payload.get("artifact_sha256") if isinstance(payload, dict) else None
    if payload.get("schema_version") != 1 or not isinstance(hashes, dict):
        return IntegrityCheck("fail", "Integritetsmanifestet har fel format.", (MANIFEST_NAME,))
    failures = []
    for name in ARTIFACT_NAMES:
        expected = hashes.get(name)
        try:
            actual = file_sha256(run_dir / name)
        except FileNotFoundError:
            failures.append(name)
            continue
        if not isinstance(expected, str) or actual != expected:
            failures.append(name)
    if payload.get("frozen_spec_sha256") != hashes.get("scenario.toml"):
        failures.append("frozen_spec_sha256")
    if payload.get("model_inputs_sha256") != hashes.get("model_inputs.json"):
        failures.append("model_inputs_sha256")
    if failures:
        return IntegrityCheck("fail", "Sparade körningsartefakter avviker från den frusna specifikationen eller modellindatan.", tuple(sorted(set(failures))))
    return IntegrityCheck("pass", "Frusen specifikation, modellindata och placeringsartefakter har verifierade SHA-256-hashar.")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
