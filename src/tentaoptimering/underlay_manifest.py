"""Manifest of a prepared underlay: what it was built from, what it contains and whether it is still current."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .paths import REPO_ROOT, SourceFiles
from .provenance import sha256_file
from .underlay_sources import file_facts

MANIFEST_NAME = "underlay.json"
SCHEMA_VERSION = 1
CONFIGURATION = {"data_preparation": REPO_ROOT / "config" / "data_preparation.toml",
                 "room_register": REPO_ROOT / "config" / "room_register.toml"}
# Files the optimiser and the room views read; an underlay without them is incomplete.
REQUIRED_FILES = ("bookings.csv", "exam_events.csv", "optimization_demands.csv", "optimization_rooms.csv", "demand_scope.csv")
STEPS = [("read", "Läser Excel-filerna"), ("normalize", "Rensar och normaliserar"), ("link", "Kopplar tentor och Ladok-uppgifter"),
         ("model", "Bygger optimeringsunderlaget"), ("write", "Skriver underlaget"), ("reports", "Skriver kvalitetsrapporter"),
         ("publish", "Publicerar underlaget")]
_COUNTED = {"bookings": "bokningsrader", "exam_events": "tentamenstillfällen", "ladok_activities": "Ladok-aktiviteter",
            "optimization_demands": "efterfrågeposter", "optimization_rooms": "salar"}


def build_manifest(source_dir: Path, processed_dir: Path, reports_dir: Path, prepared_id: str) -> dict[str, Any]:
    """Describe the underlay just written to `processed_dir`/`reports_dir`; the files must already be there."""
    run = _json(reports_dir / "run_manifest.json")
    sources = {}
    for role, label, path in SourceFiles(source_dir=source_dir).roles():
        recorded = run.get("sources", {}).get(role, {})
        sources[role] = {"label": label, "filename": path.name, "sha256": recorded.get("sha256"), **file_facts(path)}
    files = {name: {"bytes": (processed_dir / name).stat().st_size} for name in REQUIRED_FILES}
    return {
        "schema_version": SCHEMA_VERSION, "prepared_id": prepared_id, "prepared_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_dir": str(source_dir), "sources": sources,
        "configuration": {name: sha256_file(path) for name, path in CONFIGURATION.items()},
        "files": files, "counts": {key: run.get("artifacts", {}).get(key, {}).get("rows") for key in _COUNTED},
        "period": _period(processed_dir / "bookings.csv"), "quality": _quality(reports_dir),
    }


def write_manifest(manifest: dict[str, Any], processed_dir: Path) -> None:
    (processed_dir / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def underlay_status(processed_dir: Path, source_dir: str | None) -> dict[str, Any]:
    """State of the prepared underlay: current, stale (with reasons), incomplete, unverified (no manifest) or missing."""
    path = processed_dir / MANIFEST_NAME
    if not path.is_file():
        legacy = any((processed_dir / name).is_file() for name in REQUIRED_FILES)
        return {"state": "unverified" if legacy else "missing", "manifest": None, "reasons": [
            "Underlaget saknar manifest och kan inte spåras till sina källfiler. Förbered det på nytt."] if legacy else []}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": "incomplete", "manifest": None, "reasons": ["Underlagets manifest går inte att läsa. Förbered underlaget på nytt."]}
    broken = [name for name, facts in manifest.get("files", {}).items()
              if not (processed_dir / name).is_file() or (processed_dir / name).stat().st_size != facts.get("bytes")]
    if broken:
        return {"state": "incomplete", "manifest": manifest, "reasons": [f"Filer saknas eller har ändrats efter förberedelsen: {', '.join(broken)}."]}
    reasons = stale_reasons(manifest, source_dir)
    return {"state": "stale" if reasons else "current", "manifest": manifest, "reasons": reasons}


def stale_reasons(manifest: dict[str, Any], source_dir: str | None) -> list[str]:
    """Why the underlay no longer matches its inputs; empty when it is current."""
    reasons: list[str] = []
    recorded_dir = manifest.get("source_dir")
    if source_dir and recorded_dir and Path(source_dir) != Path(recorded_dir):
        reasons.append(f"Underlaget byggdes från en annan katalog ({recorded_dir}).")
    folder = Path(recorded_dir) if recorded_dir else None
    for role, facts in manifest.get("sources", {}).items():
        path = (folder / facts["filename"]) if folder else None
        if path is None or not path.is_file():
            reasons.append(f"Källfilen {facts['filename']} finns inte längre på samma plats.")
        elif (path.stat().st_size, path.stat().st_mtime_ns) != (facts.get("bytes"), facts.get("modified_ns")):
            reasons.append(f"Källfilen {facts['filename']} har ändrats efter förberedelsen.")
    for name, digest in manifest.get("configuration", {}).items():
        if name in CONFIGURATION and sha256_file(CONFIGURATION[name]) != digest:
            reasons.append(f"Konfigurationen {CONFIGURATION[name].name} har ändrats efter förberedelsen.")
    return reasons


def _json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _period(bookings_csv: Path) -> dict[str, Any]:
    dates = pd.read_csv(bookings_csv, usecols=["scheduled_date"], dtype=str, encoding="utf-8-sig")["scheduled_date"].dropna()
    dates = dates[dates != ""]
    return {"first": dates.min() if len(dates) else None, "last": dates.max() if len(dates) else None, "dated_rows": int(len(dates))}


def _quality(reports_dir: Path) -> dict[str, Any]:
    datasets = _json(reports_dir / "data_quality.json").get("datasets", {})
    findings = [item for data in datasets.values() for item in data.get("findings", [])]
    readiness = _json(reports_dir / "optimization_readiness.json").get("metrics", {})
    scope = _json(reports_dir / "demand_scope.json").get("metrics", {})
    return {"findings": len(findings), "critical_findings": sum(1 for item in findings if item.get("severity") == "critical"),
            "demand_coverage_percent": readiness.get("optimization_demand_record_coverage_percent"),
            "unresolved_activities": scope.get("unresolved_activity_count"),
            "scope_complete": scope.get("scope_complete_for_whole_population")}
