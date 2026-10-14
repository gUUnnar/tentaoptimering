"""Which of the user's changes made a run impossible: re-solve the original scenario with one change at a time.

A run is only ever compared with the scenario it was started from. Every probe is a short, separate solve that is
kept out of the user's list of saved runs. Infeasibility is proven quickly; a probe that finds no solution within
its time limit is reported as inconclusive, never as feasible.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import threading
import time
from typing import Any
from uuid import uuid4

from .app_paths import bundled_joint_catalog_path
from .app_storage import AppStorage
from .joint_inputs import run_real_subset
from .joint_scenarios import read_scenario, resolve_scenario, scenario_id_for_problem, scenario_values, write_run_snapshot
from .joint_strategy.resources import CancelToken, ExecutionBudget
from .parameter_catalog import load_parameter_catalog

FILE = "joint_diagnosis.json"
SCENARIO_COPY = "joint_scenario.toml"
PROBE_SECONDS = 30.0
SOLUTION, INFEASIBLE, INCONCLUSIVE = "solution", "infeasible", "inconclusive"
_KIND = {"optimal": SOLUTION, "feasible_not_proven": SOLUTION, "infeasible": INFEASIBLE}
# The settings that limit where and when exams may be placed, in the order they are shown.
CONSTRAINT_IDS = ("calendar.weekdays", "calendar.start_times", "window.earlier_days", "window.later_days", "calendar.start_date", "calendar.end_date",
                  "calendar.blocked_ranges", "flex.movable_types", "rooms.selection", "rooms.max_rooms_per_exam", "rooms.allow_split_across_buildings")


def _section(content: dict[str, Any], section: str) -> dict[str, Any]:
    return dict(content.get(section, {}))


def run_changes(storage: AppStorage, run_id: str, catalog_path: Path | None = None, scenarios_dir: Path | None = None) -> dict[str, Any]:
    """What the run changed compared with the scenario it was started from: parameters and the chosen period."""
    directory = storage.run_directory(run_id)
    content = read_scenario(directory / SCENARIO_COPY)
    if content is None:
        raise FileNotFoundError("Körningen har ingen sparad kopia av scenariot, så dess ändringar kan inte utredas.")
    scenario_id = scenario_id_for_problem(storage, content["scenario"]["id"], scenarios_dir)
    baseline_path, _ = resolve_scenario(storage, scenario_id, scenarios_dir)
    baseline = read_scenario(baseline_path)
    if baseline is None:
        raise FileNotFoundError("Utgångsscenariot finns inte längre, så körningens ändringar kan inte utredas.")
    catalog = load_parameter_catalog(catalog_path or bundled_joint_catalog_path())
    defaults = {item.parameter_id: item.default for item in catalog.parameters}
    changes: list[dict[str, Any]] = []
    own, base = scenario_values(content), scenario_values(baseline)
    for key in sorted(set(own) | set(base)):
        before, after = base.get(key, defaults.get(key)), own.get(key, defaults.get(key))
        if before != after:
            changes.append({"id": key, "section": "parameters", "key": key, "baseline": before, "run": after})
    own_subset, base_subset = _section(content, "subset"), _section(baseline, "subset")
    for key in sorted(set(own_subset) | set(base_subset)):
        if own_subset.get(key) != base_subset.get(key):
            changes.append({"id": f"subset.{key}", "section": "subset", "key": key, "baseline": base_subset.get(key), "run": own_subset.get(key)})
    changed = {item["id"] for item in changes}
    constraints = [{"id": key, "value": own.get(key, defaults.get(key)), "source": "changed" if key in changed else "scenario"}
                   for key in CONSTRAINT_IDS if key in defaults]
    return {"scenario_id": scenario_id, "scenario_name": baseline["scenario"].get("name", scenario_id), "changes": changes,
            "constraints": constraints, "_baseline": baseline, "_run": content}


class DiagnosisProgress:
    """How far a diagnosis job has come; read from the status route while the job runs."""

    def __init__(self, total: int) -> None:
        self._lock = threading.Lock()
        self._state = {"done": 0, "total": total, "current": None}

    def start(self, label: str) -> None:
        with self._lock:
            self._state["current"] = label

    def finish(self) -> None:
        with self._lock:
            self._state["done"] += 1
            self._state["current"] = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)


def _classify(outcome: str) -> str:
    return _KIND.get(outcome, INCONCLUSIVE)


def _with_change(baseline: dict[str, Any], change: dict[str, Any] | None) -> dict[str, Any]:
    """The original scenario, with just `change` from the run applied (or none: the original as it is)."""
    content = deepcopy(baseline)
    if change is not None:
        content.setdefault(change["section"], {})[change["key"]] = deepcopy(change["run"])
    parameters = content.setdefault("parameters", {})
    parameters["solver.time_limit_seconds"] = min(float(parameters.get("solver.time_limit_seconds", PROBE_SECONDS)), PROBE_SECONDS)
    return content


def _probe(storage: AppStorage, content: dict[str, Any], scratch: Path, cancel: CancelToken, catalog_path: Path) -> dict[str, Any]:
    path = write_run_snapshot(storage, content)
    started = time.perf_counter()
    try:
        run = run_real_subset(path, storage.processed_dir, catalog_path, scratch, warm_start="none",
                              budget=ExecutionBudget(), cancel=cancel)
    finally:
        path.unlink(missing_ok=True)
    outcome = str(run["result"]["solver"]["outcome"])
    return {"outcome": outcome, "kind": _classify(outcome), "seconds": round(time.perf_counter() - started, 1)}


def diagnose_run(storage: AppStorage, run_id: str, progress: DiagnosisProgress | None, cancel: CancelToken,
                 catalog_path: Path | None = None, scenarios_dir: Path | None = None) -> dict[str, Any]:
    """Probe the original scenario and then each change alone. Saved next to the run; nothing else is touched."""
    catalog_file = catalog_path or bundled_joint_catalog_path()
    found = run_changes(storage, run_id, catalog_file, scenarios_dir)
    baseline, changes = found["_baseline"], found["changes"]
    scratch = storage.root / ".diagnosis" / uuid4().hex
    steps = [("baseline", None, "Utgångsscenariot utan dina ändringar")] + [(item["id"], item, item["id"]) for item in changes]
    probes: list[dict[str, Any]] = []
    try:
        for step_id, change, label in steps:
            if cancel.cancelled:
                break
            if progress:
                progress.start(label)
            probes.append({"id": step_id, **_probe(storage, _with_change(baseline, change), scratch, cancel, catalog_file)})
            if progress:
                progress.finish()
    finally:
        shutil.rmtree(storage.root / ".diagnosis", ignore_errors=True)
    result = {"run_id": run_id, "scenario_id": found["scenario_id"], "probe_seconds": PROBE_SECONDS, "complete": len(probes) == len(steps),
              "probes": probes, "culprits": [item["id"] for item in probes if item["id"] != "baseline" and item["kind"] == INFEASIBLE],
              "baseline_infeasible": any(item["id"] == "baseline" and item["kind"] == INFEASIBLE for item in probes)}
    (storage.run_directory(run_id) / FILE).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def saved_diagnosis(storage: AppStorage, run_id: str) -> dict[str, Any] | None:
    path = storage.run_directory(run_id) / FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
