"""User-writable state of the local application: settings, saved joint runs and where they live."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .app_paths import default_app_data_dir


_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")


class AppStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_app_data_dir()
        self.runs_dir = self.root / "runs"
        self.snapshots_dir = self.runs_dir / ".snapshots"
        self.processed_dir = self.root / "data" / "processed"
        self.reports_dir = self.root / "reports"
        self.settings_path = self.root / "settings.json"
        for path in (self.runs_dir, self.snapshots_dir, self.processed_dir, self.reports_dir):
            path.mkdir(parents=True, exist_ok=True)

    def settings(self) -> dict[str, str | None]:
        if not self.settings_path.is_file():
            return {"source_dir": None}
        return {"source_dir": json.loads(self.settings_path.read_text(encoding="utf-8")).get("source_dir")}

    def save_settings(self, source_dir: str | None) -> dict[str, str | None]:
        if source_dir is not None and not Path(source_dir).is_dir():
            raise ValueError("Källdatakatalogen finns inte.")
        payload = {"source_dir": source_dir}
        self.settings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload

    def warm_start(self, run_id: str) -> dict[str, Any] | None:
        """The warm-start decision saved with a joint run (`joint_warm_start.json`), or None."""
        from .joint_warm_start import read_decision
        return read_decision(self.runs_dir, self._run_dir(run_id).name)

    def warm_start_candidates(self, problem_id: str | None = None) -> list[dict[str, Any]]:
        from .joint_warm_start import list_candidates
        return list_candidates(self.runs_dir, problem_id)

    def run_directory(self, run_id: str) -> Path:
        """The directory of a saved run; the id is validated so it cannot point outside the run directory."""
        return self._run_dir(run_id)

    def _run_dir(self, run_id: str) -> Path:
        if not _SAFE_RUN_ID.fullmatch(run_id):
            raise ValueError("Körnings-id har ogiltigt format.")
        candidate = (self.runs_dir / run_id).resolve()
        root = self.runs_dir.resolve()
        if candidate.parent != root:
            raise ValueError("Körnings-id måste peka direkt under resultatkatalogen.")
        return candidate
