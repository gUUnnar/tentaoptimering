"""A/B/C: the actual booking, the base optimisation and the user's own runs – listing, profiles and comparison.

A is read from the bookings, B and C from saved runs; nothing is optimised or recomputed here (see `profile_actual`,
`profile_run`, `profile_compare`). A reference is either `actual` or a run id. `actual` is always taken for the exams of
the run it is compared with, so the two sides cover the same exams; on its own it covers a plan area and period.

A run keeps its name, kind and parameters (`run_meta`, `joint_scenario.toml`); a run made on an older underlay is
marked stale and is not compared with the current booking data unless the data it was built on is the same.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .app_paths import bundled_joint_catalog_path
from .app_storage import AppStorage
from .joint_compare import _parameter_changes, run_parameters
from .joint_inputs import dataset_hash
from .joint_summary import created_at, read_json
from .parameter_catalog import load_parameter_catalog
from .profile_actual import ACTUAL, actual_profile, scope_event_ids
from .profile_compare import compare_profiles
from .profile_run import run_name, run_profile
from .run_meta import read_meta, underlay_id
from .wishes import STATUS_TEXT, WISHES_FILE, summarize_wishes

DEFAULT_PLAN_AREA = "Uppsala"
_ACTUAL_CACHE: dict[tuple, dict[str, Any]] = {}
_CACHE_SIZE = 6
_BOOKING_FILES = ("bookings.csv", "exam_events.csv", "optimization_demands.csv", "optimization_rooms.csv", "room_inventory.csv", "exam_wishes.csv",
                  "candidate_linkage.csv", "ladok_activities.csv")


def _actual(storage: AppStorage, ids: list[str]) -> dict[str, Any]:
    """A for some exams. Reading the bookings takes seconds, so the answer is kept per state of the files and set of exams."""
    folder = storage.processed_dir
    state = tuple((name, (folder / name).stat().st_mtime_ns, (folder / name).stat().st_size) if (folder / name).is_file() else (name, 0, 0) for name in _BOOKING_FILES)
    key = (str(folder.resolve()), state, tuple(ids))
    if key not in _ACTUAL_CACHE:
        if len(_ACTUAL_CACHE) >= _CACHE_SIZE:
            _ACTUAL_CACHE.pop(next(iter(_ACTUAL_CACHE)))
        _ACTUAL_CACHE[key] = actual_profile(folder, ids)
    return _ACTUAL_CACHE[key]


def _current_hash(storage: AppStorage) -> str | None:
    try:
        return dataset_hash(storage.processed_dir)
    except OSError:
        return None


def list_runs(storage: AppStorage) -> list[dict[str, Any]]:
    """Saved runs, newest first, with what the user needs to choose among them. Reads files only; nothing is validated here."""
    current = _current_hash(storage)
    rows = []
    for path in sorted((p for p in storage.runs_dir.iterdir() if p.is_dir() and not p.name.startswith(".")), key=lambda p: p.name, reverse=True):
        problem, result = read_json(path / "joint_input.json"), read_json(path / "joint_result.json")
        if problem is None or result is None:
            continue
        meta = read_meta(path)
        solver = result.get("solver") if isinstance(result.get("solver"), dict) else {}
        rows.append({
            "run_id": path.name, "name": run_name(storage, path.name, meta), "named": bool(meta and meta.get("name")), "kind": (meta or {}).get("kind", "C"),
            "base_run_id": (meta or {}).get("base_run_id"), "problem_id": problem.get("problem_id"), "created_at": (meta or {}).get("created_at") or created_at(path.name),
            "solver_outcome": solver.get("outcome"), "has_placement": bool(result.get("schedule")), "cost_ore": solver.get("objective_value_ore"),
            "exam_count": len(problem.get("demands", [])), "changes_from_base": (meta or {}).get("changes_from_base"),
            "current_underlay": None if current is None or not problem.get("dataset_hash") else problem["dataset_hash"] == current,
        })
    return rows


def _event_ids_of(storage: AppStorage, run_id: str) -> list[str]:
    problem = read_json(storage.run_directory(run_id) / "joint_input.json")
    if problem is None:
        raise FileNotFoundError("Körningen har inget sparat indata.")
    return sorted(item["exam_demand_id"].removeprefix("exam-") for item in problem.get("demands", []))


def profile(storage: AppStorage, ref: str, scope_run: str | None = None, date_from: str | None = None, date_to: str | None = None,
            include_exams: bool = True) -> dict[str, Any]:
    """The profile of `actual` (for the exams of `scope_run`, or a plan area and period) or of a saved run."""
    if ref == ACTUAL:
        ids = _event_ids_of(storage, scope_run) if scope_run else scope_event_ids(storage.processed_dir, DEFAULT_PLAN_AREA, date_from, date_to)
        found = _actual(storage, ids)
    else:
        found = run_profile(storage, ref, _current_hash(storage))
    return found if include_exams else {key: value for key, value in found.items() if key != "exams"}


def compare(storage: AppStorage, left: str, right: str) -> dict[str, Any]:
    """Compare two references. The same reference twice is refused."""
    if left == right:
        raise ValueError("Välj två olika alternativ att jämföra.")
    scope = right if left == ACTUAL else left if right == ACTUAL else None
    first, second = profile(storage, left, scope), profile(storage, right, scope)
    changes: list[dict[str, Any]] = []
    if ACTUAL not in (left, right):
        catalog = load_parameter_catalog(bundled_joint_catalog_path())
        changes = _parameter_changes(catalog, run_parameters(storage.run_directory(left)), run_parameters(storage.run_directory(right)))
    return compare_profiles(first, second, changes)


def wishes_summary(storage: AppStorage) -> dict[str, Any]:
    """How complete the business's wishes are in the prepared underlay: counts per status, and what they say about the booking."""
    path = storage.processed_dir / WISHES_FILE
    if not path.is_file():
        return {"available": False, "reason": "Underlaget innehåller inte verksamhetens önskemål ännu. Förbered underlaget igen under Underlag."}
    frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    frame = frame.assign(reason_has_letters=frame["reason_has_letters"] == "True", wish_conflict=frame["wish_conflict"] == "True",
                         order_event_count=pd.to_numeric(frame["order_event_count"]))
    return {"available": True, "status_text": STATUS_TEXT, **summarize_wishes(frame), "underlay_id": underlay_id(storage.processed_dir)}
