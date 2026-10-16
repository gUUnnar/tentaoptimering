"""File integrity and provenance checks for the saved artifacts and their data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..joint_contract import COMPATIBLE_INPUT_VERSIONS, COMPATIBLE_RESULT_VERSIONS, INPUT_SCHEMA_VERSION, RESULT_SCHEMA_VERSION
from .report import FAIL, NOT_APPLICABLE, NOT_EVALUATED, PASS, PROVENANCE, RuleResult, rule

INPUT_FILE = "joint_input.json"
RESULT_FILE = "joint_result.json"
MANIFEST_FILE = "joint_manifest.json"
DATASET_FILES = ("optimization_demands.csv", "optimization_rooms.csv", "demand_scope.csv")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_artifacts(run_dir: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, list[RuleResult]]:
    """Load the three artifacts; missing or unreadable files are reported, not raised."""
    loaded: dict[str, dict[str, Any] | None] = {}
    missing, broken = [], []
    for name in (INPUT_FILE, RESULT_FILE, MANIFEST_FILE):
        path = run_dir / name
        if not path.is_file():
            missing.append(name)
            loaded[name] = None
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("toppnivån är inte ett objekt")
            loaded[name] = value
        except (ValueError, OSError) as error:
            broken.append(f"{name}: {error}")
            loaded[name] = None
    results = [rule(
        "artifacts_present_and_readable", PROVENANCE, FAIL if (missing or broken) else PASS,
        f"saknas: {missing}; oläsbara: {broken}" if (missing or broken) else "joint_input.json, joint_result.json och joint_manifest.json finns och är läsbara.",
        missing + broken, "krav: sparade artefakter",
    )]
    return loaded[INPUT_FILE], loaded[RESULT_FILE], loaded[MANIFEST_FILE], results


def integrity_rules(
    run_dir: Path, problem: dict[str, Any], result: dict[str, Any], manifest: dict[str, Any],
    processed_dir: Path | None, config_path: Path | None, catalog_path: Path | None,
    source_dir: Path | None = None, source_manifest: Path | None = None,
) -> list[RuleResult]:
    results = []
    expected = {"input_sha256": run_dir / INPUT_FILE, "result_sha256": run_dir / RESULT_FILE}
    wrong = [key for key, path in expected.items() if manifest.get(key) != sha256(path)]
    results.append(rule(
        "manifest_hashes", PROVENANCE, FAIL if wrong else PASS,
        "Filens innehåll motsvarar inte manifestets hash: filen har ändrats efter körningen eller manifestet är fel." if wrong
        else "Indata- och resultatfilens SHA-256 stämmer med manifestet.", wrong, "krav: filernas integritet",
    ))
    versions = []
    if problem.get("schema_version") not in COMPATIBLE_INPUT_VERSIONS:
        versions.append(f"indata {problem.get('schema_version')}")
    if result.get("schema_version") not in COMPATIBLE_RESULT_VERSIONS:
        versions.append(f"resultat {result.get('schema_version')}")
    results.append(rule(
        "schema_versions", PROVENANCE, FAIL if versions else PASS,
        f"Okänd kontraktsversion: {', '.join(versions)}." if versions
        else f"Kontraktsversionerna är {INPUT_SCHEMA_VERSION} och {RESULT_SCHEMA_VERSION}.", versions, "krav: dataversioner",
    ))
    same = problem.get("problem_id") == result.get("problem_id")
    results.append(rule(
        "result_belongs_to_input", PROVENANCE, PASS if same else FAIL,
        "Resultatet hör till indatan (samma problem_id)." if same
        else f"Resultatets problem_id {result.get('problem_id')!r} skiljer sig från indatans {problem.get('problem_id')!r}.",
        reference="krav: resultat och indata hör ihop",
    ))
    results.append(_resource_pack(run_dir, problem, manifest))
    results.append(_dataset_hash(problem, processed_dir))
    results.append(_optional_hash("config_hash", manifest.get("config_sha256"), config_path, "scenariokonfigurationen"))
    results.append(_optional_hash("catalog_hash", manifest.get("catalog_sha256"), catalog_path, "parameterkatalogen"))
    results.append(_source_hashes(source_dir, source_manifest))
    return results


def _resource_pack(run_dir: Path, problem: dict[str, Any], manifest: dict[str, Any]) -> RuleResult:
    """The run's frozen copy of its resource data must be the file that the manifest recorded and the input names."""
    pack = (problem.get("resource_basis") or {}).get("pack")
    if not pack:
        return rule("resource_pack_hash", PROVENANCE, NOT_APPLICABLE, "Körningen använder ingen resursdata.", reference="krav: resursdata är spårbar")
    path = run_dir / "resource_pack.json"
    recorded = manifest.get("resource_pack_sha256")
    if not path.is_file() or not recorded:
        return rule("resource_pack_hash", PROVENANCE, FAIL, "Körningen anger resursdata men dess frysta kopia eller hash saknas.", reference="krav: resursdata är spårbar")
    same = recorded == sha256(path)
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        named = snapshot.get("sha256") == pack.get("pack_sha256") and snapshot.get("pack_id") == pack.get("pack_id")
    except (ValueError, OSError):
        named = False
    status = PASS if same and named else FAIL
    return rule("resource_pack_hash", PROVENANCE, status,
                "Den frysta resursdatan stämmer med manifestet och med den resursdata som indatan namnger." if status == PASS
                else "Den frysta resursdatan har ändrats efter körningen eller är inte den som indatan namnger.", reference="krav: resursdata är spårbar")


def _dataset_hash(problem: dict[str, Any], processed_dir: Path | None) -> RuleResult:
    if processed_dir is None:
        return rule("dataset_hash", PROVENANCE, NOT_EVALUATED, "Underlagskatalogen angavs inte; datasetets hash kan inte kontrolleras.", reference="krav: dataversioner")
    missing = [name for name in DATASET_FILES if not (processed_dir / name).is_file()]
    if missing:
        return rule("dataset_hash", PROVENANCE, NOT_EVALUATED, f"Underlagsfiler saknas: {missing}.", missing, "krav: dataversioner")
    digest = hashlib.sha256()
    for name in DATASET_FILES:
        digest.update(bytes.fromhex(sha256(processed_dir / name)))
    same = digest.hexdigest() == problem.get("dataset_hash")
    return rule("dataset_hash", PROVENANCE, PASS if same else FAIL,
                "Underlagsfilerna är oförändrade sedan körningen (hash stämmer)." if same
                else "Underlagsfilerna har ändrats sedan körningen eller hör till ett annat underlag.", reference="krav: dataversioner")


def _optional_hash(rule_id: str, recorded: object, path: Path | None, label: str) -> RuleResult:
    if path is None or not Path(path).is_file():
        return rule(rule_id, PROVENANCE, NOT_EVALUATED, f"Filen för {label} angavs inte eller finns inte; hashen kan inte kontrolleras.")
    same = recorded == sha256(Path(path))
    return rule(rule_id, PROVENANCE, PASS if same else FAIL,
                f"{label} är oförändrad sedan körningen." if same else f"{label} har ändrats sedan körningen.")


def _source_hashes(source_dir: Path | None, manifest_path: Path | None) -> RuleResult:
    if source_dir is None or manifest_path is None or not Path(manifest_path).is_file():
        return rule("source_data_hashes", PROVENANCE, NOT_EVALUATED, "Originalunderlag eller källmanifest angavs inte; rådatahashar kontrolleras inte.", reference="krav: rådata oförändrad")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    changed, absent = [], []
    for name, info in manifest.get("sources", {}).items():
        path = Path(source_dir) / info["filename"]
        if not path.is_file():
            absent.append(info["filename"])
        elif sha256(path) != info["sha256"]:
            changed.append(info["filename"])
    status = FAIL if changed else (NOT_EVALUATED if absent else PASS)
    return rule("source_data_hashes", PROVENANCE, status,
                f"Originalfiler har ändrats: {changed}." if changed else (f"Originalfiler saknas: {absent}." if absent
                else "Originalfilernas SHA-256 stämmer med källmanifestet (rådata oförändrad)."),
                changed or absent, "krav: rådata oförändrad")
