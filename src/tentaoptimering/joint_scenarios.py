"""Joint scenarios as files: the bundled ones, the user's own, and the snapshot a run is made from.

A scenario is a TOML file (schema `joint-real-subset-v1`). Bundled scenarios live in `config/scenarios` and are never
changed. A user's scenarios are kept in `joint_scenarios/` under the application data folder (a folder of its own,
not the one the older scenario page reads). A run with changed parameters is made from a snapshot: a copy of the
scenario with the changes merged into `[parameters]`. The scenario id inside the file is kept, so the run belongs to
the same problem and a warm start from the previous run of the scenario still works.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import tomllib
from typing import Any
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, Field

from .app_paths import bundled_scenarios_dir
from .app_storage import AppStorage
from .joint_selection import count_selected, describe_subset, subset_kind
from .joint_toml import dump_scenario
from .parameter_catalog import ParameterCatalog
from .parameter_validation import validate_overrides

JOINT_SCENARIO_SCHEMA = "joint-real-subset-v1"
SAFE_SCENARIO_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
USER_DIR = "joint_scenarios"
CHANGED_IN_UI = "Ändrat i gränssnittet."
BUNDLED, USER = "bundled", "user"


class ParameterValidationError(ValueError):
    """Some proposed parameter values are not acceptable; `errors` is a list of `{id, message}`."""

    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("; ".join(f"{item['id']}: {item['message']}" for item in errors))
        self.errors = errors


class ScenarioConflictError(RuntimeError):
    """A scenario name that is taken (answered as a conflict)."""


class ScenarioCreate(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")
    description: str = Field("", max_length=1000)
    base: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")
    parameters: dict[str, Any] = Field(default_factory=dict)


def user_scenarios_dir(storage: AppStorage) -> Path:
    return storage.root / USER_DIR


def read_scenario(path: Path) -> dict[str, Any] | None:
    """The content of a joint scenario file, or None if the file is not a readable joint scenario."""
    try:
        content = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    scenario, subset = content.get("scenario"), content.get("subset")
    if content.get("schema_version") != JOINT_SCENARIO_SCHEMA or not isinstance(scenario, dict) or not isinstance(subset, dict):
        return None
    return content if scenario.get("id") and isinstance(content.get("parameters", {}), dict) else None


def scenario_files(storage: AppStorage | None, bundled_dir: Path | None = None) -> list[tuple[str, Path, str]]:
    """(id, file, origin) of every joint scenario: bundled first, then the user's; a user file never hides a bundled id."""
    found: list[tuple[str, Path, str]] = []
    folders = [(bundled_dir or bundled_scenarios_dir(), BUNDLED)]
    if storage is not None:
        folders.append((user_scenarios_dir(storage), USER))
    taken: set[str] = set()
    for folder, origin in folders:
        for path in sorted(folder.glob("*.toml")) if folder.is_dir() else ():
            if SAFE_SCENARIO_ID.fullmatch(path.stem) and path.stem not in taken and read_scenario(path) is not None:
                taken.add(path.stem)
                found.append((path.stem, path, origin))
    return found


def resolve_scenario(storage: AppStorage | None, scenario_id: str, bundled_dir: Path | None = None) -> tuple[Path, str]:
    """(file, origin) of a scenario by id. A badly formed id is a ValueError, an unknown one a FileNotFoundError."""
    if not SAFE_SCENARIO_ID.fullmatch(scenario_id):
        raise ValueError("Scenarie-id har ogiltigt format.")
    for found_id, path, origin in scenario_files(storage, bundled_dir):
        if found_id == scenario_id:
            return path, origin
    raise FileNotFoundError("Scenariot finns inte bland de gemensamma scenarierna.")


def scenario_id_for_problem(storage: AppStorage | None, problem_id: Any, bundled_dir: Path | None = None) -> str | None:
    """The id that the interface uses for the scenario with this problem id (the file name); the problem id if none matches."""
    if not isinstance(problem_id, str):
        return None
    for scenario_id, path, _ in scenario_files(storage, bundled_dir):
        if (read_scenario(path) or {}).get("scenario", {}).get("id") == problem_id:
            return scenario_id
    return problem_id


def scenario_values(content: dict[str, Any]) -> dict[str, Any]:
    return dict(content.get("parameters", {}))


def effective_changes(catalog: ParameterCatalog, content: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Validate `overrides` and keep those that differ from what the scenario gives now. Raises ParameterValidationError."""
    values = scenario_values(content)
    errors = validate_overrides(catalog, overrides, values)
    if errors:
        raise ParameterValidationError(errors)
    defaults = {item.parameter_id: item.default for item in catalog.parameters}
    return {key: value for key, value in overrides.items() if value != values.get(key, defaults[key])}


def merge_changes(content: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    """A copy of the scenario with `changes` in `[parameters]` and a rationale for each; the original is not touched."""
    merged = deepcopy(content)
    merged.setdefault("parameters", {}).update(deepcopy(changes))
    merged.setdefault("rationales", {}).update({key: CHANGED_IN_UI for key in changes})
    return merged


def write_run_snapshot(storage: AppStorage, content: dict[str, Any]) -> Path:
    """Write a scenario that a run is about to use to a file of its own (the run keeps a copy of it)."""
    storage.snapshots_dir.mkdir(parents=True, exist_ok=True)
    path = storage.snapshots_dir / f"joint-{uuid4().hex}.toml"
    path.write_text(dump_scenario(content), encoding="utf-8", newline="\n")
    return path


def save_user_scenario(
    storage: AppStorage, request: ScenarioCreate, catalog: ParameterCatalog, bundled_dir: Path | None = None
) -> dict[str, Any]:
    """Save a user scenario made from `base` plus the given parameter values; refuses a name that is taken."""
    bundled = scenario_files(None, bundled_dir)
    problem_ids = {str(read_scenario(path)["scenario"]["id"]) for _, path, _ in bundled}  # type: ignore[index]
    if request.name in {item[0] for item in bundled} or request.name in problem_ids:
        raise ScenarioConflictError("Namnet krockar med ett inbyggt scenario. Välj ett annat namn.")
    target = user_scenarios_dir(storage) / f"{request.name}.toml"
    if target.exists():
        raise ScenarioConflictError("Det finns redan ett sparat scenario med det namnet.")
    base_path, _ = resolve_scenario(storage, request.base, bundled_dir)
    base = read_scenario(base_path)
    assert base is not None
    changes = effective_changes(catalog, base, request.parameters)
    content = merge_changes(base, changes)
    content["scenario"] = {"id": request.name, "name": request.name, "description": request.description, "base": request.base}
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(dump_scenario(content))
    except FileExistsError as error:
        raise ScenarioConflictError("Det finns redan ett sparat scenario med det namnet.") from error
    return scenario_row(request.name, target, USER, None)


def _exam_count(content: dict[str, Any], demands: pd.DataFrame | None) -> int | None:
    subset = content["subset"]
    if subset_kind(subset) == "event_list":
        return len(subset["exam_event_ids"])
    return count_selected(demands, subset) if demands is not None else None


def scenario_row(scenario_id: str, path: Path, origin: str, demands: pd.DataFrame | None) -> dict[str, Any]:
    """One entry of the scenario list."""
    content = read_scenario(path)
    assert content is not None
    scenario, subset = content["scenario"], content["subset"]
    try:
        kind = subset_kind(subset)
        count = _exam_count(content, demands)
        description = describe_subset(subset, count)
    except ValueError as error:
        kind, count, description = "invalid", None, f"Urvalet är ogiltigt: {error}"
    return {
        "id": scenario_id, "name": str(scenario.get("name", scenario_id)), "description": str(scenario.get("description", "")),
        "problem_id": str(scenario["id"]), "origin": origin, "schema_version": JOINT_SCENARIO_SCHEMA,
        "subset": {"plan_area": str(subset.get("plan_area", "")), "selection": "event_list" if kind == "event_list" else "rule",
                   "exam_count": count, "description": description},
    }


def scenario_rows(storage: AppStorage | None, bundled_dir: Path | None = None, processed_dir: Path | None = None) -> list[dict[str, Any]]:
    """The scenario list; exam counts of rule-based scenarios come from the prepared data when it exists."""
    demands = None
    csv = processed_dir / "optimization_demands.csv" if processed_dir is not None else None
    if csv is not None and csv.is_file():
        try:
            demands = pd.read_csv(csv, encoding="utf-8-sig", usecols=["exam_event_id", "scheduled_date", "demand_input_status", "observed_cities"])
        except (OSError, ValueError):
            demands = None
    return [scenario_row(scenario_id, path, origin, demands) for scenario_id, path, origin in scenario_files(storage, bundled_dir)]
