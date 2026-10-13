"""Routes of the diagnosis of a run without a solution: what the run changed, and which change broke it."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Path

from .app_storage import AppStorage
from .job_manager import LocalJobManager
from .joint_diagnosis import DiagnosisProgress, diagnose_run, run_changes, saved_diagnosis
from .joint_strategy.resources import CancelToken

RUN_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"


def register_diagnosis_routes(app: FastAPI, storage: AppStorage, jobs: LocalJobManager) -> None:
    latest: dict[str, dict[str, Any]] = {}  # run id -> {"job_id", "progress"} of the newest diagnosis in this process

    def job_view(run_id: str) -> dict[str, Any] | None:
        entry = latest.get(run_id)
        if entry is None:
            return None
        try:
            job = jobs.public(entry["job_id"])
        except KeyError:
            return None
        error = job.get("error") or {}
        return {"job_id": job["job_id"], "status": job["status"], "error": error.get("message") if isinstance(error, dict) else error,
                "progress": entry["progress"].snapshot()}

    @app.get("/api/joint-runs/{run_id}/diagnosis")
    def diagnosis_state(run_id: str = Path(..., pattern=RUN_ID)) -> dict[str, Any]:
        """The changes of a run compared with its scenario, the saved diagnosis (if any) and the newest diagnosis job."""
        try:
            found = run_changes(storage, run_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"scenario_id": found["scenario_id"], "scenario_name": found["scenario_name"], "changes": found["changes"],
                "saved": saved_diagnosis(storage, run_id), "job": job_view(run_id)}

    @app.post("/api/joint-runs/{run_id}/diagnosis")
    def start_diagnosis(run_id: str = Path(..., pattern=RUN_ID)) -> dict[str, Any]:
        """Start the diagnosis as a background job (one at a time, like every job); cancel it with `/api/joint-runs/{job_id}/cancel`."""
        try:
            total = len(run_changes(storage, run_id)["changes"]) + 1
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        progress, cancel = DiagnosisProgress(total), CancelToken()
        try:
            job = jobs.start(lambda: {"kind": "joint_diagnosis", **diagnose_run(storage, run_id, progress, cancel)}, cancel=cancel)
        except RuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        latest[run_id] = {"job_id": job["job_id"], "progress": progress}
        return job
