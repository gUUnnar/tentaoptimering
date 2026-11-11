"""Route of the repair suggestion: `POST /api/joint-runs/suggest-fix` with the same body as a run; the result is the job's result.

The progress of the search is read from `GET /api/joint-runs/suggest-fix/{job_id}/progress` while the job runs.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Path

from .app_storage import AppStorage
from .job_manager import LocalJobManager
from .joint_api import JointRunRequest, ParameterValidationError
from .joint_repair import RepairProgress, suggest_fix
from .joint_strategy.resources import CancelToken

JOB_ID = r"^[A-Za-z0-9]{1,64}$"


def register_repair_routes(app: FastAPI, storage: AppStorage, jobs: LocalJobManager) -> None:
    progresses: dict[str, RepairProgress] = {}

    @app.post("/api/joint-runs/suggest-fix")
    def start_suggest_fix(request: JointRunRequest) -> dict[str, Any]:
        """Search, as a background job (one at a time, like every job), for the smallest change that makes the settings possible."""
        progress, cancel = RepairProgress(), CancelToken()
        try:
            job = jobs.start(lambda: suggest_fix(storage, request, progress, cancel), cancel=cancel)
        except RuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        progresses[job["job_id"]] = progress
        return job

    @app.get("/api/joint-runs/suggest-fix/{job_id}/progress")
    def suggest_fix_progress(job_id: str = Path(..., pattern=JOB_ID)) -> dict[str, Any]:
        progress = progresses.get(job_id)
        if progress is None:
            raise HTTPException(status_code=404, detail="Okänt jobb.")
        return {"job_id": job_id, "progress": progress.snapshot()}
