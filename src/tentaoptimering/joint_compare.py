"""Compare a saved joint run with an earlier one, read from their saved artifacts (nothing is re-run).

The comparison says what differs in the parameters, what differs in the results, and whether the cost difference is
larger than the uncertainty of the search. A run that stops at its time limit has a cost (a verified upper bound) and
a lower bound; the true model optimum lies in between. A cost difference smaller than the larger of the two gaps can
therefore not be told apart from the luck of the search, and is reported as such. All amounts are model cost with the
proxy prices of the scenario, never actual cost.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .app_storage import AppStorage
from .joint_parameters import group_of
from .joint_scenarios import scenario_id_for_problem
from .joint_summary import created_at, run_summary
from .joint_validation.integrity import INPUT_FILE, RESULT_FILE
from .parameter_catalog import ParameterCatalog

PREVIOUS = "previous"
_RUN_ID = re.compile(r"^(\d{8}T\d{6})Z-(.+)$")
NO_PREVIOUS = "Ingen tidigare körning av samma scenario"
_COST_METRICS = ("cost_ore", "lower_bound_ore", "gap_ore")
_METRICS = ("cost_ore", "lower_bound_ore", "gap_ore", "changed_exams", "staff_pool_size", "rooms_used", "wall_time_seconds",
            "first_solution_seconds")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def run_parameters(directory: Path) -> dict[str, Any]:
    """The frozen parameter values of a run, from its `joint_input.json`."""
    items = _read(directory / INPUT_FILE).get("parameters", ())
    return {str(item["parameter_id"]): item.get("value") for item in items if isinstance(item, dict) and "parameter_id" in item}


def rooms_used(directory: Path) -> int | None:
    sessions = _read(directory / RESULT_FILE).get("room_sessions")
    return len({item.get("room_id") for item in sessions if isinstance(item, dict)}) if isinstance(sessions, list) else None


def find_previous(storage: AppStorage, run_id: str, problem_id: str | None) -> str | None:
    """The newest run before `run_id` of the same problem that holds a complete, verified solution."""
    match = _RUN_ID.match(run_id)
    if match is None or not problem_id:
        return None
    for path in sorted(storage.runs_dir.iterdir(), key=lambda item: item.name, reverse=True):
        other = _RUN_ID.match(path.name)
        if other is None or other.group(2) != problem_id or path.name >= run_id:
            continue
        try:
            if run_summary(storage, path.name)["has_verified_solution"]:
                return path.name
        except (FileNotFoundError, ValueError):
            continue
    return None


def _parameter_changes(catalog: ParameterCatalog, old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    groups = group_of(catalog)
    labels = {item.parameter_id: item for item in catalog.parameters}
    rows = []
    for parameter_id in sorted(set(old) | set(new)):
        if old.get(parameter_id) == new.get(parameter_id):
            continue
        definition = labels.get(parameter_id)
        rows.append({"id": parameter_id, "label": definition.label if definition else parameter_id,
                     "group": groups.get(parameter_id, "ovrigt"), "unit": definition.unit if definition else "",
                     "old": old.get(parameter_id), "new": new.get(parameter_id)})
    return rows


def _assumption_kind(parameter_id: str) -> str | None:
    """"cost" and "demand" parameters are assumptions about prices and volumes, not about how the exams are scheduled."""
    if parameter_id.startswith("cost."):
        return "cost"
    if parameter_id.startswith("demand.") or parameter_id == "digital.exam_share_pct":
        return "demand"
    return None


def assumption_changes(changes: list[dict[str, Any]]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {"cost": [], "demand": []}
    for item in changes:
        kind = _assumption_kind(str(item["id"]))
        if kind:
            found[kind].append(str(item["label"]))
    return found


def _assumption_text(found: dict[str, list[str]]) -> str:
    parts = []
    if found["cost"]:
        parts.append(f"kostnadsantagandena har ändrats ({', '.join(found['cost'])})")
    if found["demand"]:
        parts.append(f"efterfrågan har ändrats ({', '.join(found['demand'])})")
    first = " och ".join(parts)
    return (first[0].upper() + first[1:] + ". Kostnadsbelopp jämförs bara mellan körningar med samma kostnads- och efterfrågeantaganden, "
            "eftersom en skillnad annars beror på antagandena och inte på en effektivare schemaläggning. Ingen kostnadsskillnad redovisas därför. "
            "Jämför i stället salar, bemanningspool och antal flyttade tentor, som visas nedan.")


def _metric(old: Any, new: Any, with_delta: bool) -> dict[str, Any]:
    both = isinstance(old, (int, float)) and isinstance(new, (int, float))
    return {"old": old, "new": new, "delta": new - old if both and with_delta else None}


def _kronor(ore: float) -> str:
    return f"{round(abs(ore) / 100):,}".replace(",", " ") + " kr"


def interpret(delta: int | None, uncertainty: int | None) -> tuple[bool | None, str]:
    """(interpretable, Swedish sentence) for a cost difference (new minus old) and the search uncertainty, both in öre."""
    suffix = " Beloppen är modellkostnad med scenariots proxypriser, inte faktisk kostnad."
    if delta is None:
        return None, "Kostnaden kan inte jämföras eftersom en av körningarna saknar kostnad." + suffix
    if delta == 0:
        return (False if uncertainty is not None else None), "Kostnaden är oförändrad mellan körningarna." + suffix
    direction = "sjönk" if delta < 0 else "ökade"
    if uncertainty is None:
        return None, f"Kostnaden {direction} med {_kronor(delta)}. Osäkerheten går inte att beräkna eftersom gapet saknas för en av körningarna, så skillnaden kan inte tolkas." + suffix
    margin = f"osäkerheten ({_kronor(uncertainty)})"
    if abs(delta) > uncertainty:
        return True, f"Kostnaden {direction} med {_kronor(delta)}. Skillnaden är större än {margin} och kan därför tolkas." + suffix
    relation = "lika stor som" if abs(delta) == uncertainty else "mindre än"
    return False, f"Kostnaden {direction} med {_kronor(delta)}. Skillnaden är {relation} {margin} och går inte att skilja från sökningens slump." + suffix


def compare_runs(storage: AppStorage, run_id: str, base: str | None, catalog: ParameterCatalog,
                 bundled_dir: Path | None = None) -> dict[str, Any]:
    """`GET /api/joint-runs/{run_id}/compare`: `base` is a run id or `previous` (None means `previous`)."""
    current = run_summary(storage, run_id)
    base_id = find_previous(storage, run_id, current.get("problem_id")) if base in (None, PREVIOUS) else base
    header = _header(storage, run_id, current, bundled_dir)
    if base_id is None:
        return _result(header, None, False, NO_PREVIOUS, [], {}, None)
    other = run_summary(storage, base_id)
    directory, base_directory = storage.run_directory(run_id), storage.run_directory(base_id)
    reason = _incomparable(directory, base_directory, current, other)
    old_params, new_params = run_parameters(base_directory), run_parameters(directory)
    other = {**other, "rooms_used": rooms_used(base_directory)}
    current = {**current, "rooms_used": rooms_used(directory)}
    metrics = {name: _metric(other.get(name), current.get(name), reason is None) for name in _METRICS}
    gaps = [item.get("gap_ore") for item in (other, current)]
    uncertainty = max(gaps) if all(isinstance(gap, int) for gap in gaps) else None
    changes = _parameter_changes(catalog, old_params, new_params)
    if any(assumption_changes(changes).values()):
        for name in _COST_METRICS:  # N-5: amounts are compared only between runs with the same assumptions
            metrics[name] = {**metrics[name], "delta": None}
    return _result(header, _header(storage, base_id, other, bundled_dir), reason is None, reason,
                   changes, metrics, uncertainty)


def _header(storage: AppStorage, run_id: str, summary: dict[str, Any], bundled_dir: Path | None) -> dict[str, Any]:
    return {"run_id": run_id, "scenario_id": scenario_id_for_problem(storage, summary.get("problem_id"), bundled_dir), "problem_id": summary.get("problem_id"),
            "created_at": created_at(run_id), "solver_outcome": summary.get("solver_outcome"),
            "has_verified_solution": summary.get("has_verified_solution")}


def _incomparable(directory: Path, base_directory: Path, current: dict[str, Any], other: dict[str, Any]) -> str | None:
    if not (current.get("has_verified_solution") and other.get("has_verified_solution")):
        return "Minst en av körningarna saknar en fullständig verifierad lösning, så kostnaderna går inte att jämföra."
    new_input, old_input = _read(directory / INPUT_FILE), _read(base_directory / INPUT_FILE)
    if new_input.get("dataset_hash") != old_input.get("dataset_hash"):
        return "Körningarna bygger på olika dataunderlag (dataset_hash skiljer), så kostnaderna är inte jämförbara."
    ids = [{item.get("exam_demand_id") for item in data.get("demands", ()) if isinstance(item, dict)} for data in (new_input, old_input)]
    if ids[0] != ids[1]:
        return "Körningarna omfattar olika uppsättningar tentor, så kostnaderna är inte jämförbara."
    return None


def _result(run: dict[str, Any], base: dict[str, Any] | None, comparable: bool, reason: str | None,
            changes: list[dict[str, Any]], metrics: dict[str, Any], uncertainty: int | None) -> dict[str, Any]:
    cost = metrics.get("cost_ore", {})
    if base is None:
        interpretable, text = None, "Det finns ingen tidigare körning av samma scenario att jämföra med."
    elif not comparable:
        interpretable, text = None, str(reason)
    else:
        interpretable, text = interpret(cost.get("delta"), uncertainty)
        found = assumption_changes(changes)
        if found["cost"] or found["demand"]:
            # The cost difference then measures a different question: it is shown, but never called interpretable.
            interpretable = False
            text = f"{_assumption_text(found)} Beloppen är modellkostnad med scenariots proxypriser, inte faktisk kostnad."
    return {"assumption_changes": assumption_changes(changes), "run": run, "base": base, "comparable": comparable, "reason": reason, "parameter_changes": changes,
            "metrics": metrics, "uncertainty_ore": uncertainty if comparable else None, "interpretable": interpretable,
            "interpretation": text}
