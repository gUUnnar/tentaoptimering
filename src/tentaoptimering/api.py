"""FastAPI integration layer for the local React application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .app_paths import bundled_joint_catalog_path, frontend_dist_dir
from .app_storage import AppStorage
from .integrated_runs import run_integrated_term
from .integrated_validation import write_validation_report
from . import joint_api
from .job_manager import LocalJobManager
from .optimization_runs import run_optimization
from .parameter_catalog import load_parameter_catalog
from .pipeline import run_pipeline


class SettingsUpdate(BaseModel):
    source_dir: str | None = None


class ScenarioCreate(BaseModel):
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")
    source_id: str | None = None


class ScenarioUpdate(BaseModel):
    content: dict[str, Any]


def _error(error: Exception) -> HTTPException:
    if isinstance(error, joint_api.ParameterValidationError):
        return HTTPException(status_code=422, detail={"errors": error.errors})
    status = 404 if isinstance(error, FileNotFoundError) else 409 if isinstance(error, (PermissionError, RuntimeError)) else 422
    return HTTPException(status_code=status, detail=str(error))


def _summarize_run(result: dict[str, Any]) -> dict[str, Any]:
    if "solution" in result:
        solution = result["solution"]
        return {
            "run_id": result["run_id"], "scenario_id": result["scenario"]["scenario_id"],
            "status": solution["status"], "objective_ore": solution["objective_ore"],
            "room_count": solution["room_count"], "staff_pool_size": solution["anonymous_staff_pool_size"],
            "placed": result["model_completeness"]["placed_exam_demands"],
            "source_coverage": result["model_completeness"]["source_population_coverage"],
        }
    metrics = result["metrics"]
    return {
        "run_id": result["run_id"], "scenario_id": result["scenario"]["scenario_id"],
        "status": result["outcome"], "objective_ore": None, "room_count": metrics["rooms_used"],
        "staff_pool_size": None, "placed": metrics["placed_exam_count"],
        "source_coverage": None,
    }


def _flatten_parameters(value: Any, prefix: str = "") -> dict[str, object]:
    if isinstance(value, dict):
        return {
            key: item
            for name, child in value.items()
            for key, item in _flatten_parameters(child, f"{prefix}.{name}" if prefix else name).items()
        }
    if isinstance(value, list):
        return {prefix: value}
    return {prefix: value}


def _parameter_changes(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, object]]:
    first, second = _flatten_parameters(baseline), _flatten_parameters(candidate)
    return [
        {"parameter": key, "baseline": first.get(key), "candidate": second.get(key)}
        for key in sorted(set(first) | set(second))
        if first.get(key) != second.get(key)
    ]


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

    @app.get("/api/parameters")
    def parameters() -> dict[str, Any]:
        return {"parameters": storage.parameters(), "term_parameter_bindings": storage.term_parameter_bindings()}

    @app.get("/api/scenarios")
    def list_scenarios() -> dict[str, Any]:
        return {"scenarios": storage.list_scenarios()}

    @app.get("/api/scenarios/{scenario_id}")
    def get_scenario(scenario_id: str) -> dict[str, Any]:
        try:
            return storage.scenario(scenario_id)
        except Exception as error:
            raise _error(error) from error

    @app.post("/api/scenarios")
    def create_scenario(request: ScenarioCreate) -> dict[str, Any]:
        try:
            return storage.create_scenario(request.scenario_id, request.source_id)
        except Exception as error:
            raise _error(error) from error

    @app.put("/api/scenarios/{scenario_id}")
    def update_scenario(scenario_id: str, request: ScenarioUpdate) -> dict[str, Any]:
        try:
            return storage.update_scenario(scenario_id, request.content)
        except Exception as error:
            raise _error(error) from error

    @app.post("/api/scenarios/{scenario_id}/validate")
    def validate_scenario(scenario_id: str) -> dict[str, Any]:
        try:
            return storage.validate_scenario(scenario_id)
        except Exception as error:
            raise _error(error) from error

    @app.post("/api/preparation")
    def prepare() -> dict[str, Any]:
        source_dir = storage.settings()["source_dir"]
        if not source_dir:
            raise HTTPException(status_code=422, detail="Välj källdatakatalog innan underlaget förbereds.")
        return jobs.start(lambda: _prepare(storage, Path(source_dir)))

    @app.post("/api/simulations")
    def start_simulation(scenario_id: str) -> dict[str, Any]:
        try:
            snapshot = storage.create_run_snapshot(scenario_id)
            return jobs.start(lambda: _run(storage, Path(snapshot["path"]), snapshot["engine"]))
        except HTTPException:
            raise
        except Exception as error:
            raise _error(error) from error

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        try:
            return jobs.public(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/runs")
    def list_runs() -> dict[str, Any]:
        return {"runs": storage.list_runs()}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            return storage.run(run_id)
        except Exception as error:
            raise _error(error) from error

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

    @app.get("/api/runs/{run_id}/validation")
    def get_validation(run_id: str) -> dict[str, Any]:
        try:
            validation = storage.validation(run_id)
            if validation is None:
                return {"status": "not_evaluated", "reason": "Den äldre körmotorn saknar termins-eftervalideringsartefakt."}
            return validation
        except Exception as error:
            raise _error(error) from error

    @app.post("/api/runs/compare")
    def compare_runs(run_ids: list[str]) -> dict[str, Any]:
        if len(run_ids) != 2:
            raise HTTPException(status_code=422, detail="Välj exakt två körningar att jämföra.")
        try:
            rows = [_summarize_run(storage.run(run_id)) for run_id in run_ids]
            scenarios = [storage.run_scenario_content(run_id) for run_id in run_ids]
        except Exception as error:
            raise _error(error) from error
        baseline = rows[0]
        for row in rows:
            row["delta_from_first"] = {
                key: row[key] - baseline[key] if isinstance(row[key], (int, float)) and isinstance(baseline[key], (int, float)) else None
                for key in ("objective_ore", "room_count", "staff_pool_size", "placed", "source_coverage")
            }
        return {
            "baseline_run_id": baseline["run_id"], "runs": rows,
            "parameter_changes": _parameter_changes(scenarios[0], scenarios[1]),
        }

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


def _prepare(storage: AppStorage, source_dir: Path) -> dict[str, Any]:
    outputs = run_pipeline(source_dir, storage.processed_dir, storage.reports_dir)
    return {"kind": "preparation", "outputs": {key: str(value) for key, value in vars(outputs).items()}}


def _run(storage: AppStorage, scenario_path: Path, engine: str) -> dict[str, Any]:
    if engine == "integrated_term":
        run = run_integrated_term(scenario_path, storage.processed_dir, storage.runs_dir)
        validation = write_validation_report(storage.runs_dir / run["run_id"])
        return {"kind": "simulation", "run_id": run["run_id"], "validation": validation}
    run = run_optimization(scenario_path, storage.processed_dir, storage.reports_dir, storage.runs_dir)
    return {"kind": "simulation", "run_id": run["run_id"], "validation": run["validation"]}


app = create_app()
