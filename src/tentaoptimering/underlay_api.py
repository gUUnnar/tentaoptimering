"""Routes of the Underlag page: source directory, pre-check, preparation job and the state of the prepared underlay."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from .app_storage import AppStorage
from .directory_picker import choose_directory
from .job_manager import LocalJobManager
from .underlay_manifest import STEPS, underlay_status
from .underlay_prepare import PreparationProgress, prepare_underlay
from .underlay_sources import inspect_source_dir


def register_underlay_routes(app: FastAPI, storage: AppStorage, jobs: LocalJobManager) -> None:
    latest: dict[str, Any] = {}  # the newest preparation job of this server process: {"job_id", "progress"}

    def job_view() -> dict[str, Any] | None:
        if not latest:
            return None
        try:
            job = jobs.public(latest["job_id"])
        except KeyError:
            return None
        error = job.get("error") or {}
        return {"job_id": job["job_id"], "status": job["status"], "error": error.get("message") if isinstance(error, dict) else error,
                "progress": latest["progress"].snapshot(), "steps": [{"key": key, "label": label} for key, label in STEPS]}

    @app.get("/api/preparation")
    def preparation_state() -> dict[str, Any]:
        """State of the prepared underlay, the saved source directory's pre-check and the latest preparation job."""
        source_dir = storage.settings()["source_dir"]
        return {"underlay": underlay_status(storage.processed_dir, source_dir), "source": inspect_source_dir(source_dir), "job": job_view()}

    @app.post("/api/preparation")
    def prepare() -> dict[str, Any]:
        source_dir = storage.settings()["source_dir"]
        if not source_dir:
            raise HTTPException(status_code=422, detail="Välj källdatakatalog innan underlaget förbereds.")
        check = inspect_source_dir(source_dir)
        if not check["ready"]:
            missing = "\n".join(f"- {item['filename']}" for item in check["files"] if not item["found"]) or f"- katalogen {source_dir}"
            raise HTTPException(status_code=422, detail=f"Källfiler saknas:\n{missing}")
        progress = PreparationProgress()
        try:
            job = jobs.start(lambda: prepare_underlay(storage, Path(source_dir), progress))
        except RuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        latest.update(job_id=job["job_id"], progress=progress)
        return job

    @app.get("/api/source-check")
    def source_check(path: str = Query(..., max_length=1000)) -> dict[str, Any]:
        """Which expected source files a directory holds; it lists nothing else and reads no file contents."""
        return inspect_source_dir(path)

    @app.post("/api/settings/choose-source-directory")
    def choose_source_directory() -> dict[str, Any]:
        """Open Windows' folder chooser in this local process; saving the choice stays an explicit step in the page."""
        if jobs.has_active_job():
            raise HTTPException(status_code=409, detail="Källdatakatalog kan inte ändras medan ett jobb körs.")
        try:
            selected = choose_directory(storage.settings()["source_dir"])
        except RuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"source_dir": selected, "source": inspect_source_dir(selected) if selected else None}
