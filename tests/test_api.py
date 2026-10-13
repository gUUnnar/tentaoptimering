from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import uvicorn

from tentaoptimering.api import create_app
from tentaoptimering.app_storage import AppStorage


class ApiBasicsTest(unittest.TestCase):
    """The local HTTP layer outside the joint-run routes (those are tested in test_joint_api and test_joint_scenarios_api)."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.storage = AppStorage(Path(self.temporary.name))
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(create_app(self.storage.root), host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        _wait_for(lambda: self._request("GET", "/api/health")[0] == 200)

    def tearDown(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def _request(self, method: str, path: str, payload: object | None = None) -> tuple[int, dict[str, object]]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, _payload(response.read())
        except HTTPError as error:
            with error:
                return error.code, _payload(error.read())

    def test_health_and_settings(self) -> None:
        self.assertEqual(self._request("GET", "/api/health"), (200, {"status": "ok"}))
        status, settings = self._request("GET", "/api/settings")
        self.assertEqual(status, 200)
        self.assertEqual(settings["settings"], {"source_dir": None})
        self.assertEqual(settings["app_data_dir"], str(self.storage.root))
        status, saved = self._request("PUT", "/api/settings", {"source_dir": self.temporary.name})
        self.assertEqual((status, saved["settings"]), (200, {"source_dir": self.temporary.name}))
        status, _ = self._request("PUT", "/api/settings", {"source_dir": str(Path(self.temporary.name) / "saknas")})
        self.assertEqual(status, 422)

    def test_preparation_requires_a_source_directory(self) -> None:
        status, _ = self._request("POST", "/api/preparation")
        self.assertEqual(status, 422)

    def test_routes_of_the_removed_engines_do_not_exist(self) -> None:
        for path in ("/api/parameters", "/api/scenarios", "/api/scenarios/reference", "/api/runs", "/api/runs/some-run", "/api/runs/some-run/validation"):
            with self.subTest(path=path):
                status, _ = self._request("GET", path)
                self.assertEqual(status, 404)

    def test_unsafe_run_ids_are_rejected(self) -> None:
        for unsafe in ("..%2Foutside", "..%5Coutside"):
            status, _ = self._request("GET", f"/api/runs/{unsafe}/warm-start")
            self.assertIn(status, (404, 422))
        status, decision = self._request("GET", "/api/runs/no-such-run/warm-start")
        self.assertEqual((status, decision["decision"]), (200, "not_recorded"))


def _wait_for(predicate: object) -> None:
    for _ in range(100):
        try:
            if callable(predicate) and predicate():
                return
        except OSError:
            pass
        time.sleep(0.02)
    raise AssertionError("HTTP-servern startade inte.")


def _payload(body: bytes) -> dict[str, object]:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body.decode("utf-8", errors="replace")}


if __name__ == "__main__":
    unittest.main()
