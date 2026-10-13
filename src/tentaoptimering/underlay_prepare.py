"""Prepare the underlay without ever leaving a half-written one: build in a staging directory, then swap it in."""

from __future__ import annotations

from pathlib import Path
import shutil
import threading
import time
from typing import Any
from uuid import uuid4

from .app_storage import AppStorage
from .pipeline import run_pipeline
from .underlay_manifest import STEPS, build_manifest, write_manifest

_KEYS = [key for key, _ in STEPS]


class PreparationProgress:
    """Which phase a preparation job is in; read from the status route while the job runs, so it survives a page reload."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._index = -1

    def step(self, key: str) -> None:
        with self._lock:
            self._index = max(self._index, _KEYS.index(key))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            index = self._index
        label = STEPS[index][1] if index >= 0 else "Startar"
        return {"step": _KEYS[index] if index >= 0 else None, "label": label, "index": index + 1, "total": len(STEPS)}


def prepare_underlay(storage: AppStorage, source_dir: Path, progress: PreparationProgress) -> dict[str, Any]:
    """Run the pipeline into `<root>/.staging/<id>`; replace the live underlay only when it and its manifest are complete."""
    prepared_id = uuid4().hex[:12]
    _remove_leftovers(storage)
    staging = storage.root / ".staging" / prepared_id
    processed, reports = staging / "processed", staging / "reports"
    try:
        run_pipeline(source_dir, processed, reports, progress.step)
        write_manifest(build_manifest(source_dir, processed, reports, prepared_id), processed)
        progress.step("publish")
        _swap(reports, storage.reports_dir, prepared_id)
        _swap(processed, storage.processed_dir, prepared_id)
    finally:
        shutil.rmtree(storage.root / ".staging", ignore_errors=True)
        _remove_leftovers(storage)
    return {"kind": "preparation", "prepared_id": prepared_id}


def _swap(staged: Path, live: Path, token: str) -> None:
    """Replace `live` by `staged`; the old directory is put back if the replacement fails."""
    retired = live.with_name(f"{live.name}.old-{token}")
    if live.exists():
        _retry(lambda: live.rename(retired))
    try:
        _retry(lambda: staged.rename(live))
    except OSError:
        if retired.exists():
            retired.rename(live)
        raise
    shutil.rmtree(retired, ignore_errors=True)


def _retry(action: Any, attempts: int = 10) -> None:
    """Windows refuses to rename a directory some other thread is still reading; try again briefly."""
    for attempt in range(attempts):
        try:
            action()
            return
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.2)


def _remove_leftovers(storage: AppStorage) -> None:
    for live in (storage.processed_dir, storage.reports_dir):
        for old in live.parent.glob(f"{live.name}.old-*"):
            shutil.rmtree(old, ignore_errors=True)
