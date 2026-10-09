"""User-owned scenarios, settings, and saved run inspection for the local UI."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import tomllib
from typing import Any
from uuid import uuid4

from .app_paths import bundled_parameters_path, bundled_scenarios_dir, default_app_data_dir


_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")


def _read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _scenario_engine(content: dict[str, Any]) -> str:
    return "integrated_term" if "calendar" in content else "legacy_capacity"


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _quote(value)
    if isinstance(value, (int, float)):
        return str(value).lower()
    if isinstance(value, list) and not any(isinstance(item, dict) for item in value):
        return "[" + ", ".join(_toml_scalar(item) for item in value) + "]"
    raise ValueError(f"Värdet kan inte sparas i TOML: {value!r}")


def dump_toml(content: dict[str, Any]) -> str:
    """Write the subset of TOML used by the project without another dependency."""
    lines: list[str] = []

    def write_table(table: dict[str, Any], prefix: str | None = None, array: bool = False) -> None:
        scalar_items = [(key, value) for key, value in table.items() if not isinstance(value, dict) and not (isinstance(value, list) and any(isinstance(item, dict) for item in value))]
        if prefix is not None:
            lines.append(f"[[{prefix}]]" if array else f"[{prefix}]")
        lines.extend(f"{key} = {_toml_scalar(value)}" for key, value in scalar_items)
        if scalar_items:
            lines.append("")
        for key, value in table.items():
            child = key if prefix is None else f"{prefix}.{key}"
            if isinstance(value, dict):
                write_table(value, child)
            elif isinstance(value, list) and any(isinstance(item, dict) for item in value):
                if not all(isinstance(item, dict) for item in value):
                    raise ValueError(f"Blandad lista stöds inte för {child}.")
                for item in value:
                    write_table(item, child, array=True)

    write_table(content)
    return "\n".join(lines).rstrip() + "\n"


class AppStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_app_data_dir()
        self.scenarios_dir = self.root / "scenarios"
        self.runs_dir = self.root / "runs"
        self.snapshots_dir = self.runs_dir / ".snapshots"
        self.processed_dir = self.root / "data" / "processed"
        self.reports_dir = self.root / "reports"
        self.settings_path = self.root / "settings.json"
        for path in (self.scenarios_dir, self.runs_dir, self.snapshots_dir, self.processed_dir, self.reports_dir):
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

    def parameters(self) -> list[dict[str, Any]]:
        return _read_toml(bundled_parameters_path())["parameter"]

    def _user_path(self, scenario_id: str) -> Path:
        if not _SAFE_ID.fullmatch(scenario_id):
            raise ValueError("Scenarie-id får bara innehålla gemener, siffror, bindestreck och understreck.")
        return self.scenarios_dir / f"{scenario_id}.toml"

    def _record(self, scenario_id: str, path: Path, origin: str) -> dict[str, Any]:
        content = _read_toml(path)
        return {
            "id": scenario_id,
            "name": content.get("scenario_id", scenario_id),
            "description": content.get("description", ""),
            "engine": _scenario_engine(content),
            "origin": origin,
            "editable": origin == "user",
        }

    def list_scenarios(self) -> list[dict[str, Any]]:
        records = [self._record(path.stem, path, "bundled") for path in bundled_scenarios_dir().glob("*.toml")]
        records.extend(self._record(path.stem, path, "user") for path in self.scenarios_dir.glob("*.toml"))
        return sorted(records, key=lambda item: (item["origin"] != "user", item["id"]))

    def scenario(self, scenario_id: str) -> dict[str, Any]:
        user_path = self._user_path(scenario_id)
        path = user_path if user_path.is_file() else bundled_scenarios_dir() / f"{scenario_id}.toml"
        if not path.is_file():
            raise FileNotFoundError("Scenariot finns inte.")
        record = self._record(scenario_id, path, "user" if path == user_path else "bundled")
        record["content"] = _read_toml(path)
        return record

    def create_scenario(self, scenario_id: str, source_id: str | None = None) -> dict[str, Any]:
        target = self._user_path(scenario_id)
        if target.exists():
            raise ValueError("Ett användarscenario med samma id finns redan.")
        source = self.scenario(source_id) if source_id else self.scenario("integrated_term_exploratory")
        content = deepcopy(source["content"])
        content["scenario_id"] = scenario_id
        content["description"] = f"Kopia av {source['name']}."
        target.write_text(dump_toml(content), encoding="utf-8")
        return self.scenario(scenario_id)

    def update_scenario(self, scenario_id: str, content: dict[str, Any]) -> dict[str, Any]:
        path = self._user_path(scenario_id)
        if not path.is_file():
            raise PermissionError("Endast användarscenarier kan ändras. Kopiera först det inbyggda scenariot.")
        if content.get("scenario_id") != scenario_id:
            raise ValueError("scenario_id i innehållet måste matcha scenarie-id.")
        temporary = path.with_suffix(".pending.toml")
        try:
            temporary.write_text(dump_toml(content), encoding="utf-8")
            self._validate_path(temporary, _scenario_engine(content))
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return self.scenario(scenario_id)

    def validate_scenario(self, scenario_id: str) -> dict[str, Any]:
        scenario = self.scenario(scenario_id)
        path = self._user_path(scenario_id) if scenario["origin"] == "user" else bundled_scenarios_dir() / f"{scenario_id}.toml"
        self._validate_path(path, scenario["engine"])
        return {"valid": True, "engine": scenario["engine"], "scenario_id": scenario_id}

    def scenario_path(self, scenario_id: str) -> Path:
        scenario = self.scenario(scenario_id)
        return self._user_path(scenario_id) if scenario["origin"] == "user" else bundled_scenarios_dir() / f"{scenario_id}.toml"

    def create_run_snapshot(self, scenario_id: str) -> dict[str, str]:
        """Freeze validated scenario bytes before queuing a calculation."""
        scenario = self.scenario(scenario_id)
        source = self.scenario_path(scenario_id)
        snapshot_id = uuid4().hex
        target = self.snapshots_dir / f"{snapshot_id}.toml"
        target.write_bytes(source.read_bytes())
        try:
            self._validate_path(target, scenario["engine"])
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return {"snapshot_id": snapshot_id, "path": str(target), "engine": scenario["engine"]}

    def list_runs(self) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        for path in self.runs_dir.iterdir():
            result_path = path / "result.json"
            if not result_path.is_file():
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            solution = result.get("solution", result.get("metrics", {}))
            runs.append({"run_id": path.name, "scenario_id": result.get("scenario", {}).get("scenario_id"), "created_at": result.get("created_at_utc", path.name), "status": solution.get("status", result.get("outcome", "unknown")), "engine": "integrated_term" if "solution" in result else "legacy_capacity"})
        return sorted(runs, key=lambda item: item["created_at"], reverse=True)

    def run(self, run_id: str) -> dict[str, Any]:
        path = self._run_dir(run_id) / "result.json"
        if not path.is_file():
            raise FileNotFoundError("Körningen finns inte.")
        return json.loads(path.read_text(encoding="utf-8"))

    def validation(self, run_id: str) -> dict[str, Any] | None:
        path = self._run_dir(run_id) / "validation.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def run_scenario_content(self, run_id: str) -> dict[str, Any]:
        path = self._run_dir(run_id) / "scenario.toml"
        if not path.is_file():
            raise FileNotFoundError("Körningens frysta scenario saknas.")
        return _read_toml(path)

    def _run_dir(self, run_id: str) -> Path:
        if not _SAFE_RUN_ID.fullmatch(run_id):
            raise ValueError("Körnings-id har ogiltigt format.")
        candidate = (self.runs_dir / run_id).resolve()
        root = self.runs_dir.resolve()
        if candidate.parent != root:
            raise ValueError("Körnings-id måste peka direkt under resultatkatalogen.")
        return candidate

    @staticmethod
    def _validate_path(path: Path, engine: str) -> None:
        if engine == "integrated_term":
            from .integrated_config import load_integrated_term_scenario
            load_integrated_term_scenario(path)
        else:
            from .optimizer_config import load_scenario_config
            load_scenario_config(path)

    def import_bundled_frontend(self) -> None:
        """Kept for packaging hooks; user state never contains web assets."""
        return None
