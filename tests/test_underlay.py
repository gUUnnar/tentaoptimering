from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import uvicorn

from tentaoptimering.api import create_app
from tentaoptimering.app_storage import AppStorage
from tentaoptimering.paths import SourceFiles
from tentaoptimering.underlay_manifest import MANIFEST_NAME, REQUIRED_FILES, underlay_status
from tentaoptimering.underlay_prepare import PreparationProgress, prepare_underlay
from tentaoptimering.underlay_sources import inspect_source_dir

STEPS = ("read", "normalize", "link", "model", "write", "reports")


def _fake_pipeline(source_dir: Path, processed: Path, reports: Path, step=None, marker: str = "ny") -> None:
    """Stands in for `run_pipeline`: writes the files the manifest builder reads."""
    for name in STEPS:
        if step:
            step(name)
    processed.mkdir(parents=True)
    reports.mkdir(parents=True)
    for name in REQUIRED_FILES:
        (processed / name).write_text("scheduled_date\n2026-01-05\n2026-01-09\n" if name == "bookings.csv" else marker, encoding="utf-8")
    (reports / "run_manifest.json").write_text(json.dumps({"sources": {}, "artifacts": {"bookings": {"rows": 2}}}), encoding="utf-8")


def _sources(folder: Path) -> Path:
    folder.mkdir(exist_ok=True)
    for _role, _label, path in SourceFiles(source_dir=folder).roles():
        path.write_text("x", encoding="utf-8")
    return folder


class UnderlayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.storage = AppStorage(self.root / "app")
        self.source = _sources(self.root / "kallor")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _prepare(self, pipeline=_fake_pipeline) -> PreparationProgress:
        progress = PreparationProgress()
        with patch("tentaoptimering.underlay_prepare.run_pipeline", pipeline):
            prepare_underlay(self.storage, self.source, progress)
        return progress

    def test_precheck_names_missing_files(self) -> None:
        self.assertTrue(inspect_source_dir(self.source)["ready"])
        SourceFiles(source_dir=self.source).bookings.unlink()
        check = inspect_source_dir(self.source)
        self.assertFalse(check["ready"])
        self.assertEqual([item["found"] for item in check["files"]], [False, True, True])
        self.assertFalse(inspect_source_dir(self.root / "saknas")["exists"])
        self.assertFalse(inspect_source_dir(None)["ready"])

    def test_status_follows_the_source_files(self) -> None:
        self.assertEqual(underlay_status(self.storage.processed_dir, str(self.source))["state"], "missing")
        progress = self._prepare()
        self.assertEqual(progress.snapshot()["step"], "publish")
        status = underlay_status(self.storage.processed_dir, str(self.source))
        self.assertEqual((status["state"], status["manifest"]["period"]["first"], status["manifest"]["counts"]["bookings"]), ("current", "2026-01-05", 2))
        changed = SourceFiles(source_dir=self.source).ladok
        changed.write_text("ändrad", encoding="utf-8")
        os.utime(changed, ns=(1, 1))
        status = underlay_status(self.storage.processed_dir, str(self.source))
        self.assertEqual(status["state"], "stale")
        self.assertIn(changed.name, status["reasons"][0])
        other = self.root / "annan"
        other.mkdir()
        self.assertTrue(any("annan katalog" in reason for reason in underlay_status(self.storage.processed_dir, str(other))["reasons"]))

    def test_underlay_without_manifest_or_with_a_missing_file_is_not_current(self) -> None:
        self._prepare()
        (self.storage.processed_dir / "demand_scope.csv").unlink()
        self.assertEqual(underlay_status(self.storage.processed_dir, None)["state"], "incomplete")
        (self.storage.processed_dir / MANIFEST_NAME).unlink()
        self.assertEqual(underlay_status(self.storage.processed_dir, None)["state"], "unverified")

    def test_failed_preparation_keeps_the_previous_underlay(self) -> None:
        self._prepare()
        before = (self.storage.processed_dir / "exam_events.csv").read_text(encoding="utf-8")

        def failing(source_dir, processed, reports, step=None):
            _fake_pipeline(source_dir, processed, reports, step, marker="halv")
            raise ValueError("kraschade mitt i")

        with self.assertRaises(ValueError):
            self._prepare(failing)
        self.assertEqual((self.storage.processed_dir / "exam_events.csv").read_text(encoding="utf-8"), before)
        self.assertEqual(underlay_status(self.storage.processed_dir, str(self.source))["state"], "current")
        self.assertFalse((self.storage.root / ".staging").exists())
        self.assertEqual(list(self.storage.root.glob("**/*.old-*")), [])

    def test_a_new_preparation_replaces_the_underlay(self) -> None:
        self._prepare()
        self._prepare(lambda s, p, r, step=None: _fake_pipeline(s, p, r, step, marker="nyare"))
        self.assertEqual((self.storage.processed_dir / "exam_events.csv").read_text(encoding="utf-8"), "nyare")
        self.assertEqual(list(self.storage.root.glob("**/*.old-*")), [])


class UnderlayRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(create_app(self.root / "app"), host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        for _ in range(200):
            try:
                if self._call("GET", "/api/health")[0] == 200:
                    break
            except OSError:
                time.sleep(0.02)

    def tearDown(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def _call(self, method: str, path: str, payload: object | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_state_before_any_preparation(self) -> None:
        _, state = self._call("GET", "/api/preparation")
        self.assertEqual((state["underlay"]["state"], state["job"], state["source"]["ready"]), ("missing", None, False))

    def test_preparation_is_refused_when_source_files_are_missing(self) -> None:
        self._call("PUT", "/api/settings", {"source_dir": str(self.root)})
        status, body = self._call("POST", "/api/preparation")
        self.assertEqual(status, 422)
        self.assertIn(SourceFiles(source_dir=self.root).bookings.name, body["detail"])

    def test_source_check_and_chooser(self) -> None:
        folder = _sources(self.root / "kallor")
        quoted = str(folder).replace("\\", "%5C").replace(":", "%3A")
        self.assertTrue(self._call("GET", f"/api/source-check?path={quoted}")[1]["ready"])
        missing = str(self.root / "saknas").replace("\\", "%5C").replace(":", "%3A")
        self.assertFalse(self._call("GET", f"/api/source-check?path={missing}")[1]["exists"])
        with patch("tentaoptimering.underlay_api.choose_directory", return_value=str(folder)) as picker:
            _, chosen = self._call("POST", "/api/settings/choose-source-directory")
        self.assertEqual((chosen["source_dir"], chosen["source"]["ready"]), (str(folder), True))
        picker.assert_called_once_with(None)
        self.assertIsNone(self._call("GET", "/api/settings")[1]["settings"]["source_dir"])
        with patch("tentaoptimering.underlay_api.choose_directory", return_value=None):
            self.assertEqual(self._call("POST", "/api/settings/choose-source-directory")[1], {"source_dir": None, "source": None})

    def test_preparation_job_reports_progress_and_final_state(self) -> None:
        folder = _sources(self.root / "kallor")
        self._call("PUT", "/api/settings", {"source_dir": str(folder)})
        with patch("tentaoptimering.underlay_prepare.run_pipeline", _fake_pipeline):
            _, job = self._call("POST", "/api/preparation")
            state: dict = {}
            for _ in range(200):
                state = self._call("GET", "/api/preparation")[1]
                if state["job"]["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.05)
        self.assertEqual((state["job"]["job_id"], state["job"]["status"], state["underlay"]["state"]), (job["job_id"], "completed", "current"))
        self.assertEqual(state["job"]["progress"]["total"], len(state["job"]["steps"]))


if __name__ == "__main__":
    unittest.main()
