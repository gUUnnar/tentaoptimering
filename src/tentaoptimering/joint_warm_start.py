"""Earlier saved runs as warm starts for the joint optimizer.

A warm start names an earlier run by its run id, as in `runs/<run_id>/joint_result.json`. Saved run
artifacts and their identifiers are the only storage; the decision about a warm start is written next to
the new run's own artifacts (`joint_warm_start.json`).

This module decides whether an earlier run is a trustworthy *candidate*:

* its artifacts are intact (the SHA-256 hashes in its manifest match the files);
* it holds a complete placement;
* the independent post-validation is run on it now and finds it technically correct. The stored
  `joint_validation.json` is never taken as proof, it can only make the candidate worse.

Whether the placement fits the new instance and its rules is not decided here. That is the solver's exact
day-by-day re-check (joint_strategy/warm_start.py), which is always made. A candidate is a starting point, never
an answer.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .joint_contract import RESULT_SCHEMA_VERSION, JointOptimizationInput
from .joint_validation import validate_run
from .joint_validation.integrity import INPUT_FILE, MANIFEST_FILE, RESULT_FILE, sha256
from .joint_validation.run import VALIDATION_JSON

WARM_START_FILE = "joint_warm_start.json"
WARM_START_SCHEMA = "joint-warm-start-v1"
AUTO = "auto"
NONE = "none"
AUTO_CANDIDATES = 5  # how many of the newest runs of the same problem are inspected in automatic mode
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")


@dataclass(frozen=True)
class StartSource:
    """An earlier run that passed the candidate checks."""

    run_id: str
    result: dict[str, Any]
    problem_id: str | None
    dataset_hash: str | None
    result_sha256: str
    parameters: dict[str, Any]
    technical_validation: str

    def summary(self) -> dict[str, Any]:
        solver = self.result.get("solver") or {}
        return {
            "run_id": self.run_id, "problem_id": self.problem_id, "result_sha256": self.result_sha256,
            "solver_outcome": solver.get("outcome"), "cost_ore": solver.get("objective_value_ore"),
            "technical_validation_now": self.technical_validation,
        }


@dataclass(frozen=True)
class StartChoice:
    """The outcome of looking for a warm start: the chosen run, if any, and why others were passed over."""

    requested: str
    source: StartSource | None
    considered: tuple[dict[str, Any], ...]

    @property
    def start(self) -> dict[str, Any] | None:
        return self.source.result if self.source else None


def inspect_run(runs_dir: Path, run_id: str) -> tuple[StartSource | None, list[str]]:
    """The run as a warm-start candidate, or the reasons it cannot be one."""
    if not _SAFE_RUN_ID.fullmatch(run_id):
        return None, ["Körnings-id har ogiltigt format."]
    root = Path(runs_dir).resolve()
    run_dir = (root / run_id).resolve()
    if run_dir.parent != root or not run_dir.is_dir():
        return None, [f"Körningen {run_id} finns inte under resultatkatalogen."]
    missing = [name for name in (INPUT_FILE, RESULT_FILE, MANIFEST_FILE) if not (run_dir / name).is_file()]
    if missing:
        return None, [f"Körningens artefakter saknas: {', '.join(missing)}."]
    try:
        problem, result, manifest = (json.loads((run_dir / name).read_text(encoding="utf-8")) for name in (INPUT_FILE, RESULT_FILE, MANIFEST_FILE))
    except (OSError, ValueError) as error:
        return None, [f"Körningens artefakter kan inte läsas: {error}."]
    if not all(isinstance(item, dict) for item in (problem, result, manifest)):
        return None, ["Körningens artefakter har fel struktur."]
    digest = sha256(run_dir / RESULT_FILE)
    if manifest.get("result_sha256") != digest or manifest.get("input_sha256") != sha256(run_dir / INPUT_FILE):
        return None, ["Körningens filer stämmer inte med manifestets SHA-256: de har ändrats efter körningen."]
    if result.get("schema_version") != RESULT_SCHEMA_VERSION:
        return None, [f"Okänd resultatversion: {result.get('schema_version')}."]
    solver = result.get("solver") if isinstance(result.get("solver"), dict) else {}
    coverage = result.get("coverage") if isinstance(result.get("coverage"), dict) else {}
    if solver.get("outcome") not in ("optimal", "feasible_not_proven") or not result.get("schedule") or not coverage.get("technical_placement_complete"):
        return None, [f"Körningen har ingen fullständig placering (utfall: {solver.get('outcome')})."]
    stored = _stored_validation(run_dir)
    if stored in ("fail",):
        return None, ["Den sparade eftervalideringen av körningen är underkänd."]
    summary = validate_run(run_dir)["summary"]  # run again now: a stored verdict is not evidence
    if not summary["technically_validated"]:
        return None, [f"Den oberoende eftervalideringen av körningen godkänner den inte nu (teknisk: {summary['technical_validation']}, ursprung: {summary['provenance']})."]
    parameters = {str(item.get("parameter_id")): item.get("value") for item in problem.get("parameters", ()) if isinstance(item, dict)}
    return StartSource(run_id, result, problem.get("problem_id"), problem.get("dataset_hash"), digest, parameters, summary["technical_validation"]), []


def _stored_validation(run_dir: Path) -> str | None:
    path = run_dir / VALIDATION_JSON
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return str(value["summary"]["technical_validation"])
    except (OSError, ValueError, KeyError, TypeError):
        return "fail"


def find_start(runs_dir: Path, problem: JointOptimizationInput, requested: str | None = AUTO) -> StartChoice:
    """Pick the warm start for a new run: none, one named run, or the newest usable run of the same problem."""
    requested = (requested or NONE).strip() or NONE
    if requested == NONE:
        return StartChoice(NONE, None, ())
    names = [requested] if requested != AUTO else _newest_runs_of(Path(runs_dir), problem.problem_id)
    considered: list[dict[str, Any]] = []
    for name in names:
        source, reasons = inspect_run(Path(runs_dir), name)
        if source is not None and requested == AUTO and source.problem_id != problem.problem_id:
            source, reasons = None, [f"Körningen gäller ett annat problem ({source.problem_id})."]
        considered.append({"run_id": name, "usable_candidate": source is not None, "reasons": reasons})
        if source is not None:
            return StartChoice(requested, source, tuple(considered))
    return StartChoice(requested, None, tuple(considered))


def _newest_runs_of(runs_dir: Path, problem_id: str) -> list[str]:
    if not runs_dir.is_dir():
        return []
    found = []
    for path in runs_dir.iterdir():
        if not (path / MANIFEST_FILE).is_file() or not (path / INPUT_FILE).is_file() or not _SAFE_RUN_ID.fullmatch(path.name):
            continue
        try:
            if json.loads((path / INPUT_FILE).read_text(encoding="utf-8")).get("problem_id") == problem_id:
                found.append(path.name)
        except (OSError, ValueError, AttributeError):
            continue
    return sorted(found, reverse=True)[:AUTO_CANDIDATES]  # run ids start with their UTC time


def changed_parameters(source: StartSource | None, problem: JointOptimizationInput) -> list[str]:
    """Parameters whose value differs between the earlier run and the new instance (information only)."""
    if source is None:
        return []
    new = {item.parameter_id: item.value for item in problem.parameters}
    return sorted(key for key in set(new) | set(source.parameters)
                  if json.dumps(new.get(key), sort_keys=True, default=str) != json.dumps(source.parameters.get(key), sort_keys=True, default=str))


def decision_record(choice: StartChoice, problem: JointOptimizationInput, report: Any, budget: Any) -> dict[str, Any]:
    """What `joint_warm_start.json` holds: the request, the candidate checks, the solver's re-check and the resources."""
    source = choice.source
    status = report.status if source is not None else "not_used"
    return {
        "schema_version": WARM_START_SCHEMA,
        "requested": choice.requested,
        "decision": status,
        "explanation": explain(choice, report),
        "candidates_considered": list(choice.considered),
        "source": source.summary() if source else None,
        "source_dataset_differs": bool(source and source.dataset_hash != problem.dataset_hash),
        "changed_parameters": changed_parameters(source, problem),
        "recheck": report.to_dict() if source is not None else None,
        "execution": budget.describe() if budget is not None else None,
    }


def explain(choice: StartChoice, report: Any) -> str:
    if choice.source is None:
        if choice.requested == NONE:
            return "Ingen varmstart begärdes."
        reasons = "; ".join(f"{item['run_id']}: {' '.join(item['reasons'])}" for item in choice.considered)
        return "Ingen tidigare körning kunde användas som startpunkt" + (f" ({reasons})." if reasons else ": ingen tidigare körning av samma problem hittades.")
    run = choice.source.run_id
    if report.status == "accepted":
        return (f"Placeringen från {run} klarade den exakta kontrollen mot de nya reglerna och blev första verifierade lösning "
                f"efter {report.first_solution_seconds:.1f} s.")
    if report.status == "hint_only":
        return f"Placeringen från {run} används bara som ledtråd i den monolitiska strategin."
    return (f"Placeringen från {run} kunde inte återanvändas som helhet: {' '.join(report.reasons)} "
            f"{report.hint_exams} tentors tidigare pass användes som ledtråd; vanlig optimering gjordes.")


def read_decision(runs_dir: Path, run_id: str) -> dict[str, Any] | None:
    """The saved warm-start decision of a run, for the interface; None for a run that has none."""
    if not _SAFE_RUN_ID.fullmatch(run_id):
        raise ValueError("Körnings-id har ogiltigt format.")
    path = Path(runs_dir) / run_id / WARM_START_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def list_candidates(runs_dir: Path, problem_id: str | None = None) -> list[dict[str, Any]]:
    """Saved joint runs that could be offered as a warm start, newest first (a quick listing for a picker).

    Nothing is validated here: the listing only reads the saved result and stored verdict. A run is accepted
    as a start only by `find_start`, which checks the files and validates them again.
    """
    runs_dir = Path(runs_dir)
    if not runs_dir.is_dir():
        return []
    rows = []
    for name in sorted((path.name for path in runs_dir.iterdir()), reverse=True):
        directory = runs_dir / name
        if not _SAFE_RUN_ID.fullmatch(name) or not all((directory / item).is_file() for item in (INPUT_FILE, RESULT_FILE, MANIFEST_FILE)):
            continue
        try:
            problem = json.loads((directory / INPUT_FILE).read_text(encoding="utf-8"))
            result = json.loads((directory / RESULT_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(problem, dict) or not isinstance(result, dict) or (problem_id is not None and problem.get("problem_id") != problem_id):
            continue
        solver = result.get("solver") if isinstance(result.get("solver"), dict) else {}
        rows.append({
            "run_id": name, "problem_id": problem.get("problem_id"), "solver_outcome": solver.get("outcome"),
            "cost_ore": solver.get("objective_value_ore"), "has_placement": bool(result.get("schedule")),
            "stored_technical_validation": _stored_validation(directory),
            "warm_start_decision": (read_decision(runs_dir, name) or {}).get("decision"),
        })
    return rows


def write_decision(run_dir: Path, record: dict[str, Any]) -> None:
    (Path(run_dir) / WARM_START_FILE).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def report_lines(record: dict[str, Any]) -> list[str]:
    recheck = record.get("recheck") or {}
    lines = ["", "## Varmstart och beräkningsresurser", "",
             f"- Begärd varmstart: `{record['requested']}`; beslut: `{record['decision']}`.", f"- {record['explanation']}"]
    if record.get("source"):
        lines.append(f"- Startkörning: `{record['source']['run_id']}` (kostnad {record['source']['cost_ore']} öre, "
                     f"oberoende teknisk kontroll nu: `{record['source']['technical_validation_now']}`).")
        if record["changed_parameters"]:
            lines.append(f"- Ändrade parametrar sedan startkörningen: {', '.join(record['changed_parameters'])}.")
        if recheck.get("verified_cost_ore") is not None:
            lines.append(f"- Kostnad för den omkontrollerade startplaceringen i den nya instansen: {recheck['verified_cost_ore']} öre.")
    if recheck.get("first_solution_seconds") is not None:
        lines.append(f"- Första verifierade lösning efter {recheck['first_solution_seconds']:.1f} s (källa: {recheck['first_solution_source']}).")
    if record.get("execution"):
        lines.append(f"- Beräkningsresurser: {record['execution']['threads']} trådar, {record['execution']['memory_mb']} MB, "
                     f"parallella dagkontroller: {record['execution']['parallel_day_checks']}.")
    lines.append("- Ingen lösning godkänns av att den tidigare varit godkänd: placeringen kontrolleras alltid mot de nya reglerna.")
    return lines
