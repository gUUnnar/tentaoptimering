"""FastAPI integration layer for the local React application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .app_paths import bundled_joint_catalog_path, frontend_dist_dir
from .app_storage import AppStorage
from .booking_api import register_booking_routes
from . import joint_api
from .job_manager import LocalJobManager
from .joint_diagnosis_api import register_diagnosis_routes
from .joint_precheck_api import register_precheck_routes
from .joint_savings_api import register_savings_routes
from .parameter_catalog import load_parameter_catalog
from .underlay_api import register_underlay_routes


class SettingsUpdate(BaseModel):
    source_dir: str | None = None


def _error(error: Exception) -> HTTPException:
    if isinstance(error, joint_api.ParameterValidationError):
        return HTTPException(status_code=422, detail={"errors": error.errors})
    status = 404 if isinstance(error, FileNotFoundError) else 409 if isinstance(error, (PermissionError, RuntimeError)) else 422
    return HTTPException(status_code=status, detail=str(error))


def create_app(storage_root: Path | None = None) -> FastAPI:
    storage = AppStorage(storage_root)
    jobs = LocalJobManager()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            jobs.shutdown()

    app = FastAPI(title="Tentaoptimering", version="0.1.0", lifespan=lifespan)
    app.state.storage = storage
    app.state.jobs = jobs

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/settings")
    def get_settings() -> dict[str, Any]:
        return {"settings": storage.settings(), "app_data_dir": str(storage.root)}

    @app.put("/api/settings")
    def update_settings(update: SettingsUpdate) -> dict[str, Any]:
        try:
            if jobs.has_active_job():
                raise RuntimeError("Källdatakatalog kan inte ändras medan ett jobb körs.")
            return {"settings": storage.save_settings(update.source_dir)}
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        try:
            return jobs.public(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    register_booking_routes(app, storage)
    register_underlay_routes(app, storage, jobs)
    register_diagnosis_routes(app, storage, jobs)
    register_savings_routes(app, storage, jobs)
    register_precheck_routes(app, storage, jobs)

    @app.get("/api/joint-runs/warm-start-candidates")
    def warm_start_candidates(problem_id: str | None = None) -> dict[str, Any]:
        """Saved joint runs that can be offered as a warm start. Listing only: the solver re-checks any choice."""
        return {"candidates": storage.warm_start_candidates(problem_id)}

    @app.get("/api/joint-runs/scenarios")
    def joint_scenarios() -> dict[str, Any]:
        """Scenarios that the joint engine can run: the bundled ones and the user's own."""
        return {"scenarios": joint_api.list_scenarios(storage=storage, processed_dir=storage.processed_dir)}

    @app.post("/api/joint-runs/scenarios")
    def create_joint_scenario(request: joint_api.ScenarioCreate) -> dict[str, Any]:
        """Save a user scenario: a bundled or saved one plus changed parameter values."""
        try:
            return joint_api.create_scenario(storage, request)
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/joint-runs/parameters")
    def joint_parameters(scenario: str = Query(..., pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")) -> dict[str, Any]:
        """Every parameter of the catalog with default, the scenario's value and whether the engine supports it."""
        try:
            return joint_api.parameters_payload(storage, scenario)
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/joint-runs/options")
    def joint_options(scenario: str = Query(..., pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")) -> dict[str, Any]:
        """The rooms and exam types of a scenario, for choosing `rooms.selection` and `flex.movable_types`."""
        try:
            return joint_api.options_payload_for(storage, scenario)
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/joint-runs/period")
    def joint_period(
        scenario: str = Query(..., pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$"),
        date_from: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"), date_to: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ) -> dict[str, Any]:
        """Which periods the data allows (coverage), and with both dates the check of that period."""
        try:
            return joint_api.period_payload_for(storage, scenario, date_from, date_to)
        except Exception as error:
            raise _error(error) from error

    @app.post("/api/joint-runs")
    def start_joint_run(request: joint_api.JointRunRequest) -> dict[str, Any]:
        """Start a joint run as a background job; follow it with `/api/joint-runs/{job_id}/events`."""
        try:
            return joint_api.start_joint_run(jobs, storage, request)
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/joint-runs/{job_id}/events")
    def joint_job_events(job_id: str, after: int = Query(0, ge=0)) -> dict[str, Any]:
        try:
            return joint_api.job_events(jobs, job_id, after)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except Exception as error:
            raise _error(error) from error

    @app.post("/api/joint-runs/{job_id}/cancel")
    def cancel_joint_run(job_id: str) -> dict[str, Any]:
        try:
            return joint_api.cancel_job(jobs, job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/joint-runs/{run_id}/summary")
    def joint_run_summary(run_id: str) -> dict[str, Any]:
        try:
            return joint_api.run_summary(storage, run_id)
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/joint-runs/{run_id}/compare")
    def joint_run_compare(run_id: str, base: str = Query("previous", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")) -> dict[str, Any]:
        """Compare a run with `base` (a run id, or `previous`: the closest earlier verified run of the same scenario)."""
        try:
            return joint_api.compare_runs(storage, run_id, base, load_parameter_catalog(bundled_joint_catalog_path()))
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/runs/{run_id}/events")
    def saved_run_events(run_id: str) -> dict[str, Any]:
        """The whole saved event log of a finished joint run, for replay."""
        try:
            return joint_api.run_events(storage, run_id)
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/runs/{run_id}/warm-start")
    def get_warm_start(run_id: str) -> dict[str, Any]:
        try:
            decision = storage.warm_start(run_id)
            if decision is None:
                return {"decision": "not_recorded", "explanation": "Körningen har ingen sparad varmstartsbeskrivning."}
            return decision
        except Exception as error:
            raise _error(error) from error

    dist = frontend_dist_dir()
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API-resursen finns inte.")
            candidate = (dist / path).resolve()
            root = dist.resolve()
            if path and candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
