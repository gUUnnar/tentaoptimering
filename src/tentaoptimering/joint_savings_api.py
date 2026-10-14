"""Routes of the savings potential of a run: the numbers, and the job that solves referensen med låsta datum for it."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Path

from .app_storage import AppStorage
from .job_manager import LocalJobManager
from .joint_savings import compute_baseline, savings
from .joint_strategy.resources import CancelToken

RUN_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"


def register_savings_routes(app: FastAPI, storage: AppStorage, jobs: LocalJobManager) -> None:
    latest: dict[str, str] = {}  # run id -> id of the newest referensen med låsta datum job of this process

    def job_view(run_id: str) -> dict[str, Any] | None:
        try:
            job = jobs.public(latest[run_id])
        except KeyError:
            return None
        error = job.get("error") or {}
        return {"job_id": job["job_id"], "status": job["status"], "error": error.get("message") if isinstance(error, dict) else error}

    @app.get("/api/joint-runs/{run_id}/savings")
    def savings_state(run_id: str = Path(..., pattern=RUN_ID)) -> dict[str, Any]:
        """Savings potential against referensen med låsta datum (state, numbers, reason) and the newest job that computes referensen med låsta datum."""
        try:
            return {**savings(storage, run_id), "job": job_view(run_id)}
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/joint-runs/{run_id}/savings")
    def start_savings(run_id: str = Path(..., pattern=RUN_ID)) -> dict[str, Any]:
        """Solve referensen med låsta datum for the run as a background job; cancel it with `/api/joint-runs/{job_id}/cancel`."""
        if savings(storage, run_id).get("state") == "unavailable":
            raise HTTPException(status_code=422, detail=savings(storage, run_id)["reason"])
        cancel = CancelToken()
        try:
            job = jobs.start(lambda: compute_baseline(storage, run_id, cancel), cancel=cancel)
        except RuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        latest[run_id] = job["job_id"]
        return job
