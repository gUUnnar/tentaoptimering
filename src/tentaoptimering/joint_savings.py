"""Savings potential of a run: the model cost of the locked-date reference (no exam is moved) minus the cost of the run.

The reference is the same scenario, data and cost assumptions with no exam type movable, so every exam keeps its booked
occasion while rooms and staffing are still planned as cheaply as possible. It is an *optimisation run* (a kind of C run with
the dates locked), not the actual booking: the actual booking (A) is read from the bookings and is never optimised (see
`profile_actual`). The difference is a *theoretical* annual potential in model cost. It is not a verified, realisable saving:
contracts, notice periods and avoidability of the costs are not modelled (see docs/KOSTNADSMODELL.md).
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .app_paths import bundled_joint_catalog_path
from .app_storage import AppStorage
from .joint_inputs import run_real_subset
from .joint_scenarios import read_scenario, write_run_snapshot
from .joint_strategy.resources import CancelToken, ExecutionBudget
from .joint_toml import dump_scenario

SCENARIO_COPY = "joint_scenario.toml"
BASELINE_TIME_LIMIT_SECONDS = 120.0
VERIFIED = ("optimal", "feasible_not_proven")
COMPONENTS = (("annual_room_cost_ore", "Lokaler"), ("annual_staff_pool_cost_ore", "Vaktpool"),
              ("external_room_session_cost_ore", "Externa salstillfällen"), ("staff_session_cost_ore", "Rörlig bemanning"))


def baseline_content(content: dict[str, Any]) -> dict[str, Any]:
    """The scenario of a run with no flexibility: no exam type may use another occasion than its historical one."""
    baseline = deepcopy(content)
    parameters = baseline.setdefault("parameters", {})
    parameters["flex.movable_types"] = []
    parameters["solver.time_limit_seconds"] = min(float(parameters.get("solver.time_limit_seconds", BASELINE_TIME_LIMIT_SECONDS)),
                                                  BASELINE_TIME_LIMIT_SECONDS)
    baseline.setdefault("rationales", {})["flex.movable_types"] = "Låsta datum: ingen tentamen flyttas från sitt bokade tillfälle (referensoptimering, inte den faktiska bokningen)."
    return baseline


def _underlay_id(storage: AppStorage) -> str:
    try:
        return str(json.loads((storage.processed_dir / "underlay.json").read_text(encoding="utf-8")).get("prepared_id", ""))
    except (OSError, ValueError):
        return ""


def baseline_key(storage: AppStorage, content: dict[str, Any]) -> str:
    """The same locked-date reference is reused for every run with the same scenario and underlay; any change gives a new one."""
    text = dump_scenario(baseline_content(content)) + "\n" + _underlay_id(storage)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _verified(directory: Path) -> dict[str, Any] | None:
    """The cost facts of a saved run if it has a verified solution (solver outcome, complete placement, passed validation)."""
    result, validation = _read(directory / "joint_result.json"), _read(directory / "joint_validation.json")
    if not result or not validation or not isinstance(result.get("costs"), dict):
        return None
    solver, coverage = result.get("solver") or {}, result.get("coverage") or {}
    if solver.get("outcome") not in VERIFIED or not coverage.get("technical_placement_complete"):
        return None
    if (validation.get("summary") or {}).get("technical_validation") != "pass":
        return None
    return {"cost_ore": solver.get("objective_value_ore"), "bound_ore": solver.get("best_objective_bound_ore"), "costs": result["costs"],
            "staff_pool_size": result.get("staff_pool_size"), "changed_exams": result.get("changed_exam_demands"),
            "exams_total": coverage.get("exam_demands_total")}


def _baseline_directory(storage: AppStorage, key: str) -> Path | None:
    root = storage.root / "baselines" / key
    runs = sorted(path for path in root.glob("*") if path.is_dir()) if root.is_dir() else []
    return runs[-1] if runs else None


def savings(storage: AppStorage, run_id: str) -> dict[str, Any]:
    """State and numbers of the savings potential of a run; `state` is unavailable, missing (not computed yet) or ready."""
    directory = storage.run_directory(run_id)
    content = read_scenario(directory / SCENARIO_COPY)
    run = _verified(directory)
    if content is None:
        return {"state": "unavailable", "reason": "Körningen har ingen sparad kopia av scenariot, så referensen med låsta datum kan inte beräknas."}
    if run is None:
        return {"state": "unavailable", "reason": "Körningen har ingen verifierad lösning att jämföra med referensen med låsta datum."}
    key = baseline_key(storage, content)
    baseline_dir = _baseline_directory(storage, key)
    base = _verified(baseline_dir) if baseline_dir else None
    if baseline_dir is not None and base is None:
        return {"state": "unavailable", "key": key, "reason": "Referensen med låsta datum hittade ingen verifierad lösning (till exempel för att ursprungstillfällena inte ryms i de valda salarna), så ingen besparing kan redovisas."}
    if base is None:
        return {"state": "missing", "key": key}
    low = (base["bound_ore"] if base["bound_ore"] is not None else base["cost_ore"]) - run["cost_ore"]
    high = base["cost_ore"] - (run["bound_ore"] if run["bound_ore"] is not None else run["cost_ore"])
    components = [{"key": field, "label": label, "baseline_ore": base["costs"].get(field), "run_ore": run["costs"].get(field)}
                  for field, label in COMPONENTS if base["costs"].get(field) or run["costs"].get(field)]
    return {"state": "ready", "key": key, "baseline": base, "run": run, "potential_ore": base["cost_ore"] - run["cost_ore"],
            "potential_low_ore": low, "potential_high_ore": high, "components": components}


def compute_baseline(storage: AppStorage, run_id: str, cancel: CancelToken, catalog_path: Path | None = None) -> dict[str, Any]:
    """Solve the locked-date reference for a run (or reuse the saved one). It is kept apart from the user's runs."""
    content = read_scenario(storage.run_directory(run_id) / SCENARIO_COPY)
    if content is None:
        raise FileNotFoundError("Körningen har ingen sparad kopia av scenariot, så referensen med låsta datum kan inte beräknas.")
    key = baseline_key(storage, content)
    if _baseline_directory(storage, key) is None:
        target = storage.root / "baselines" / key
        snapshot = write_run_snapshot(storage, baseline_content(content))
        try:
            run_real_subset(snapshot, storage.processed_dir, catalog_path or bundled_joint_catalog_path(), target, warm_start="none",
                            budget=ExecutionBudget(), cancel=cancel)
        except BaseException:
            shutil.rmtree(target, ignore_errors=True)
            raise
        finally:
            snapshot.unlink(missing_ok=True)
        if cancel.cancelled:
            shutil.rmtree(target, ignore_errors=True)
    return {"kind": "joint_baseline", "key": key}
