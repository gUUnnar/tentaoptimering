"""Small single-worker job manager for non-blocking local calculations."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
import threading
from typing import Any, Callable
from uuid import uuid4


class LocalJobManager:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tentaoptimering")
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start(self, action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            if any(job["status"] in {"queued", "running"} for job in self._jobs.values()):
                raise RuntimeError("En beräkning pågår redan. Vänta tills den är klar.")
            job_id = uuid4().hex
            job = {"job_id": job_id, "status": "queued", "created_at": _now(), "result": None, "error": None}
            self._jobs[job_id] = job
            future = self._executor.submit(self._execute, job_id, action)
            job["future"] = future
            return self._public_job(job)

    def _execute(self, job_id: str, action: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            self._jobs[job_id]["status"] = "running"
            self._jobs[job_id]["started_at"] = _now()
        try:
            result = action()
        except Exception as error:
            with self._lock:
                self._jobs[job_id].update(status="failed", error={"type": type(error).__name__, "message": str(error)}, finished_at=_now())
            return
        with self._lock:
            self._jobs[job_id].update(status="completed", result=result, finished_at=_now())

    def public(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError("Körningsjobbet finns inte.")
            return self._public_job(self._jobs[job_id])

    def has_active_job(self) -> bool:
        with self._lock:
            return any(job["status"] in {"queued", "running"} for job in self._jobs.values())

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _public_job(job: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in job.items() if key != "future"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
