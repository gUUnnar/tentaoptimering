"""Joint optimisation runs through the local API: start, observe, cancel, replay and summarise.

The functions here hold the logic behind the `/api/joint-runs` and `/api/runs/{run_id}/events` routes, so that
they can be used (and tested) without an HTTP server. Observation never changes a run: the events come from a
`ProgressSink` that the solver only writes to, and the summary is read from the saved artifacts.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .app_paths import bundled_joint_catalog_path
from .app_storage import AppStorage
from .job_manager import LocalJobManager
from .joint_compare import compare_runs
from .joint_inputs import run_real_subset
from .joint_options import options_payload, room_selection_errors
from .joint_period import PeriodRequest, coverage_payload, period_report, with_period
from .joint_parameters import describe_parameters
from .joint_progress import EVENTS_FILE, ProgressSink, read_events
from .joint_scenarios import (
    JOINT_SCENARIO_SCHEMA, ParameterValidationError, ScenarioConflictError, ScenarioCreate, effective_changes,
    merge_changes, read_scenario, resolve_scenario, save_user_scenario, scenario_rows, scenario_values, write_run_snapshot,
)
from .joint_strategy.resources import CancelToken, ExecutionBudget
from .joint_summary import run_summary
from .parameter_catalog import load_parameter_catalog

__all__ = [
    "JOINT_SCENARIO_SCHEMA", "JointRunRequest", "ParameterValidationError", "ScenarioConflictError", "ScenarioCreate",
    "cancel_job", "compare_runs", "create_scenario", "job_events", "list_scenarios", "options_payload_for", "period_payload_for",
    "parameters_payload", "run_events", "run_summary", "scenario_path", "start_joint_run",
]
RUNNING, COMPLETED, FAILED, CANCELLED = "running", "completed", "failed", "cancelled"


class JointRunRequest(BaseModel):
    scenario: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")
    warm_start: str = Field("auto", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")  # "auto", "none" or a run id
    threads: int = Field(0, ge=0, le=512)
    memory_mb: int | None = Field(None, ge=1)
    parallel_day_checks: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)  # changes relative to the scenario: {parameter id: value}
    period: PeriodRequest | None = None  # planning period chosen in the interface; None = the scenario's own


def list_scenarios(
    scenarios_dir: Path | None = None, storage: AppStorage | None = None, processed_dir: Path | None = None
) -> list[dict[str, Any]]:
    """The joint scenarios that can be run: bundled (from `scenarios_dir`) and, if a storage is given, the user's own."""
    return scenario_rows(storage, scenarios_dir, processed_dir)


def scenario_path(scenario_id: str, scenarios_dir: Path | None = None, storage: AppStorage | None = None) -> Path:
    """The file of a joint scenario; only ids from `list_scenarios` are accepted."""
    return resolve_scenario(storage, scenario_id, scenarios_dir)[0]


def parameters_payload(
    storage: AppStorage, scenario_id: str, scenarios_dir: Path | None = None, catalog_path: Path | None = None
) -> dict[str, Any]:
    """Every catalog parameter with its default and the value this scenario gives it (`GET /api/joint-runs/parameters`)."""
    path, _ = resolve_scenario(storage, scenario_id, scenarios_dir)
    content = read_scenario(path) or {}
    return describe_parameters(load_parameter_catalog(catalog_path or bundled_joint_catalog_path()), scenario_id, scenario_values(content))


def period_payload_for(
    storage: AppStorage, scenario_id: str, date_from: str | None = None, date_to: str | None = None, scenarios_dir: Path | None = None
) -> dict[str, Any]:
    """Data coverage for the period picker; with both dates also the check of that period (`GET /api/joint-runs/period`)."""
    path, _ = resolve_scenario(storage, scenario_id, scenarios_dir)
    area = str((read_scenario(path) or {}).get("subset", {}).get("plan_area", ""))
    payload = coverage_payload(storage.processed_dir, area)
    payload["scenario_id"] = scenario_id
    payload["check"] = None
    if date_from and date_to:
        try:
            first, last = date.fromisoformat(date_from), date.fromisoformat(date_to)
        except ValueError as error:
            raise ValueError("Datum måste anges som ÅÅÅÅ-MM-DD.") from error
        payload["check"] = period_report(storage.processed_dir, area, first, last)
    return payload


def options_payload_for(storage: AppStorage, scenario_id: str, scenarios_dir: Path | None = None) -> dict[str, Any]:
    """The rooms and exam types that the scenario can be tuned with (`GET /api/joint-runs/options`)."""
    path, _ = resolve_scenario(storage, scenario_id, scenarios_dir)
    return options_payload(storage.processed_dir, scenario_id, read_scenario(path) or {})


def _check_rooms(processed_dir: Path, content: dict[str, Any], changes: dict[str, Any]) -> None:
    """Refuse a `rooms.selection` that names a room the scenario's plan area does not have (when the data is there)."""
    if "rooms.selection" in changes:
        errors = room_selection_errors(processed_dir, content, changes["rooms.selection"])
        if errors:
            raise ParameterValidationError(errors)


def create_scenario(
    storage: AppStorage, request: ScenarioCreate, scenarios_dir: Path | None = None, catalog_path: Path | None = None,
    processed_dir: Path | None = None,
) -> dict[str, Any]:
    """Save a user scenario (`POST /api/joint-runs/scenarios`); returns its entry as the scenario list shows it."""
    catalog = load_parameter_catalog(catalog_path or bundled_joint_catalog_path())
    base_path, _ = resolve_scenario(storage, request.base, scenarios_dir)
    base = read_scenario(base_path) or {}
    effective_changes(catalog, base, request.parameters)  # type errors first, then the room check
    _check_rooms(processed_dir or storage.processed_dir, base, request.parameters)
    save_user_scenario(storage, request, catalog, scenarios_dir)
    return next(row for row in scenario_rows(storage, scenarios_dir, processed_dir or storage.processed_dir) if row["id"] == request.name)


def start_joint_run(
    jobs: LocalJobManager, storage: AppStorage, request: JointRunRequest,
    scenarios_dir: Path | None = None, catalog_path: Path | None = None,
) -> dict[str, Any]:
    """Queue a joint run as a background job with its own cancel token and progress sink.

    Parameter changes in the request are validated first and merged into a snapshot of the scenario; the scenario
    file itself is never changed. The snapshot is removed when the run ends (the run keeps a copy of it).
    """
    original, _ = resolve_scenario(storage, request.scenario, scenarios_dir)
    catalog_file = catalog_path or bundled_joint_catalog_path()
    config, snapshot = original, None
    if request.parameters or request.period:
        content = read_scenario(original) or {}
        changes = effective_changes(load_parameter_catalog(catalog_file), content, request.parameters)
        _check_rooms(storage.processed_dir, content, request.parameters)
        merged = merge_changes(content, changes)
        if request.period:
            clash = sorted({"calendar.start_date", "calendar.end_date"} & set(request.parameters))
            if clash:
                raise ValueError(f"Perioden sätter {', '.join(clash)}; ändra inte samma datum som parameter.")
            merged = with_period(merged, storage.processed_dir, request.period)
        if changes or request.period:
            config = snapshot = write_run_snapshot(storage, merged)
    cancel, progress = CancelToken(), ProgressSink()
    budget = ExecutionBudget(request.threads, request.memory_mb, request.parallel_day_checks)

    def action() -> dict[str, Any]:
        try:
            run = run_real_subset(config, storage.processed_dir, catalog_file, storage.runs_dir, warm_start=request.warm_start,
                                  budget=budget, cancel=cancel, progress=progress)
        except Exception as error:
            if not progress.has("finished"):
                progress.emit("finished", outcome="failed", cost_ore=None, bound_ore=None, cancelled=cancel.cancelled,
                              error=f"{type(error).__name__}: {error}")
            raise
        finally:
            progress.close()
            if snapshot is not None:
                snapshot.unlink(missing_ok=True)
        finished = [event for event in progress.events() if event["type"] == "finished"]
        return {"kind": "joint_run", "run_id": run["run_id"], "validation": run["validation"],
                "cancelled": bool(finished[-1]["cancelled"]) if finished else cancel.cancelled}

    try:
        job = jobs.start(action, cancel=cancel, progress=progress)
    except Exception:
        if snapshot is not None:
            snapshot.unlink(missing_ok=True)
        raise
    return {**job, "run_id": None}


def job_events(jobs: LocalJobManager, job_id: str, after: int = 0) -> dict[str, Any]:
    """The events of a running or finished joint job after sequence number `after`."""
    job, _, progress = jobs.handle(job_id)
    if progress is None:
        raise ValueError("Jobbet är inte en gemensam optimeringskörning.")
    status = job["status"]
    result = job.get("result") or {}
    state = RUNNING if status in ("queued", "running") else FAILED if status == "failed" else (
        CANCELLED if result.get("cancelled") else COMPLETED)
    payload: dict[str, Any] = {"status": state, "events": progress.events(after), "last_seq": progress.last_seq,
                               "run_id": result.get("run_id") or progress.run_id,
                               "elapsed_seconds": _elapsed(job, progress, state)}
    if state == FAILED:
        error = job.get("error")
        # A readable string: the client shows it as text. The job record itself keeps {type, message}.
        payload["error"] = f"{error.get('type')}: {error.get('message')}" if isinstance(error, dict) else (str(error) if error else None)
    return payload


def _elapsed(job: dict[str, Any], progress: ProgressSink, state: str) -> float:
    """The run's time in seconds: live while it runs, the time of the last event once it is over."""
    if state == RUNNING:
        return progress.elapsed()
    events = progress.events()
    return float(events[-1]["t"]) if events else progress.elapsed()


def cancel_job(jobs: LocalJobManager, job_id: str) -> dict[str, Any]:
    """Ask a running joint job to stop; the best verified solution found so far is saved, if there is one."""
    requested = jobs.cancel(job_id)
    return {"job_id": job_id, "cancel_requested": requested, "status": jobs.public(job_id)["status"]}


def run_events(storage: AppStorage, run_id: str) -> dict[str, Any]:
    """The whole saved event log of a finished run, for replay."""
    path = storage.run_directory(run_id) / EVENTS_FILE
    if not path.is_file():
        raise FileNotFoundError("Körningen har ingen sparad händelselogg.")
    events = read_events(path)
    return {"run_id": run_id, "events": events, "last_seq": events[-1]["seq"] if events else 0}
