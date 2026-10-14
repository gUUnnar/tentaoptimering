"""What a saved run records about itself, apart from the engine's own artifacts: its name, kind, parent and provenance.

A run is never overwritten: every start makes a new directory. `joint_run.json` in that directory says

* `kind`: `B` (the base optimisation: the base scenario exactly as defined, nothing changed) or `C` (a user-steered run:
  any other parameter set or period). The same engine runs both; only the parameter values differ;
* `name`: what the user called it (or a default), `base_run_id`: the run it was started from, if any;
* `underlay_id`: which prepared underlay (`underlay.json`, `prepared_id`) and `dataset_hash` it was built on, and
  `model`: the engine, contract and parameter catalog versions. A run is comparable with another, or with the actual
  booking (A), only when these match what is current; `staleness` says it.

The parameter values themselves are in the run's own `joint_scenario.toml` and `joint_input.json`; nothing is copied here.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from . import __version__
from .joint_contract import INPUT_SCHEMA_VERSION, RESULT_SCHEMA_VERSION
from .parameter_catalog import load_parameter_catalog
from .provenance import sha256_file

META_FILE = "joint_run.json"
SCHEMA = "joint-run-meta-v1"
BASE_SCENARIO_ID = "joint_base"
KIND_BASE, KIND_USER = "B", "C"
MAX_NAME = 120


def model_version(catalog_path: Path) -> dict[str, str]:
    return {"engine": __version__, "input_schema": INPUT_SCHEMA_VERSION, "result_schema": RESULT_SCHEMA_VERSION,
            "catalog_version": load_parameter_catalog(catalog_path).version, "catalog_sha256": sha256_file(catalog_path)}


def underlay_id(processed_dir: Path) -> str | None:
    try:
        return str(json.loads((processed_dir / "underlay.json").read_text(encoding="utf-8")).get("prepared_id") or "") or None
    except (OSError, ValueError):
        return None


def run_kind(problem_id: str, changes: dict[str, Any], period: bool) -> str:
    """B only for the base scenario run exactly as defined; everything else (changed value, own period, other base) is C."""
    return KIND_BASE if problem_id == BASE_SCENARIO_ID and not changes and not period else KIND_USER


def clean_name(name: str | None) -> str | None:
    text = " ".join(str(name or "").split())[:MAX_NAME]
    return text or None


def default_name(kind: str, scenario_name: str, changed_labels: list[str], now: datetime | None = None) -> str:
    when = (now or datetime.now()).strftime("%H:%M")
    if kind == KIND_BASE:
        return f"B – Grundoptimering, {when}"
    shown = ", ".join(changed_labels[:2]) + (f" m.fl. ({len(changed_labels)})" if len(changed_labels) > 2 else "")
    return f"C – {shown or scenario_name}, {when}"


def write_meta(run_dir: Path, meta: dict[str, Any]) -> None:
    (run_dir / META_FILE).write_text(json.dumps({"schema": SCHEMA, **meta}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_meta(run_dir: Path) -> dict[str, Any] | None:
    try:
        value = json.loads((run_dir / META_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) and value.get("schema") == SCHEMA else None


def new_meta(*, name: str | None, kind: str, scenario_id: str, base_run_id: str | None, changes: dict[str, Any], period: dict[str, Any] | None,
             processed_dir: Path, catalog_path: Path, dataset_hash: str | None = None) -> dict[str, Any]:
    return {
        "name": clean_name(name), "kind": kind, "scenario_id": scenario_id, "base_run_id": base_run_id,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "changes_from_base": changes, "period": period,
        "underlay_id": underlay_id(processed_dir), "dataset_hash": dataset_hash, "model": model_version(catalog_path),
    }


def staleness(meta: dict[str, Any] | None, current_underlay: str | None, run_dataset_hash: str | None, current_dataset_hash: str | None) -> dict[str, Any]:
    """Whether the run was built on the underlay that is current now. Different data means the results must not be set side by side unchecked."""
    if run_dataset_hash is not None and current_dataset_hash is not None and run_dataset_hash != current_dataset_hash:
        return {"current": False, "reason": "Körningen byggdes på ett annat underlag än det som gäller nu (dataunderlagets kontrollsumma skiljer). Den räknas inte om och jämförs inte med den faktiska bokningen utan att du godkänner det."}
    if meta and meta.get("underlay_id") and current_underlay and meta["underlay_id"] != current_underlay:
        return {"current": True, "reason": "Underlaget har förberetts om sedan körningen, men de data som används är oförändrade."}
    return {"current": True, "reason": None}
