"""Route of the pre-check: `POST /api/joint-runs/precheck` with the same body as a run; follow the job at `/api/jobs/{id}`."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from .app_storage import AppStorage
from .job_manager import LocalJobManager
from .joint_api import JointRunRequest, ParameterValidationError, run_config
from .joint_precheck import precheck
from .joint_strategy.resources import CancelToken


def register_precheck_routes(app: FastAPI, storage: AppStorage, jobs: LocalJobManager) -> None:
    @app.post("/api/joint-runs/precheck")
    def start_precheck(request: JointRunRequest) -> dict[str, Any]:
        """Check as a background job (one at a time, like every job) whether the settings can place every exam."""
        cancel = CancelToken()
        try:
            config, snapshot = run_config(storage, request)  # bad values are refused here, per parameter, before anything is queued
        except ParameterValidationError as error:
            raise HTTPException(status_code=422, detail={"errors": error.errors}) from error
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        try:
            return jobs.start(lambda: precheck(storage, config, snapshot, cancel), cancel=cancel)
        except RuntimeError as error:
            if snapshot is not None:
                snapshot.unlink(missing_ok=True)
            raise HTTPException(status_code=409, detail=str(error)) from error
