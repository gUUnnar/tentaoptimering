"""The validation as part of the run flow, the CLI and the real 12-exam regression."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tentaoptimering.cli import main  # noqa: E402
from tentaoptimering.joint_inputs import run_real_subset  # noqa: E402
from tentaoptimering.joint_validation import validate_run, write_validation  # noqa: E402
from tentaoptimering.paths import default_source_dir  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "config" / "joint_parameter_catalog.toml"
SUBSET = REPO_ROOT / "config" / "scenarios" / "joint_real_subset.toml"
PROCESSED = REPO_ROOT / "data" / "processed"

PAIR_SCENARIO = """schema_version = "joint-real-subset-v1"
[scenario]
id = "pair"
description = "d"
[subset]
plan_area = "Uppsala"
exam_event_ids = ["X", "Y"]
[parameters]
"calendar.start_times" = ["08:00", "14:00"]
"staffing.ladder" = [{max_participants = 60, required_staff = 1}]
"cost.room_annual_per_seat_ore" = 100
"cost.staff_annual_ore" = 1000
"solver.time_limit_seconds" = 10.0
"solver.workers" = 1
"""


def _write_pair_dataset(path: Path) -> Path:
    def row(event: str) -> dict[str, object]:
        return {
            "exam_event_id": event, "activity_id": f"act-{event}", "demand_input_status": "ready_provisional_ladok_demand",
            "scheduled_date": "2026-01-12", "booking_start_time": "08:00", "scheduled_time": "08:00-12:00",
            "observed_exam_types": "Ordinarie tenta", "observed_digital_exam_values": "Nej", "observed_cities": "Uppsala",
            "demand_value": 50, "demand_measure_source_field": "registered_count", "course_code": f"C-{event}",
        }
    pd.DataFrame([row("X"), row("Y")]).to_csv(path / "optimization_demands.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([
        {"room_id": room, "reference_address": address, "reference_city": "Uppsala", "capacity_seats": 60,
         "digital_capability_status": "all_places_support_e_exam", "eligible_for_exploratory_capacity_poc": True,
         "available_from": None, "available_to": None}
        for room, address in (("uu-r1", "Adress 1"), ("uu-r2", "Adress 2"))
    ]).to_csv(path / "optimization_rooms.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"activity_id": ["act-X", "act-Y"], "scope_status": ["included", "included"]}).to_csv(
        path / "demand_scope.csv", index=False, encoding="utf-8-sig")
    scenario = path / "scenario.toml"
    scenario.write_text(PAIR_SCENARIO, encoding="utf-8")
    return scenario


class RunFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.scenario = _write_pair_dataset(self.dir)
        self.runs = self.dir / "runs"

    def _run(self) -> tuple[dict, Path]:
        run = run_real_subset(self.scenario, self.dir, CATALOG, self.runs)
        return run, self.runs / run["run_id"]

    def test_validation_runs_automatically_and_keeps_the_three_verdicts_apart(self) -> None:
        run, directory = self._run()
        summary = run["validation"]
        self.assertEqual(summary["solver_status"]["reported_outcome"], "optimal")
        self.assertEqual(summary["technical_validation"], "pass")
        self.assertEqual(summary["business_verification"], "not_evaluated")
        self.assertTrue(summary["technically_validated"])
        for name in ("joint_validation.json", "joint_validation.md"):
            self.assertTrue((directory / name).is_file(), name)
        report = (directory / "joint_report.md").read_text(encoding="utf-8")
        self.assertIn("Oberoende eftervalidering", report)
        self.assertIn("Verksamhetsmässig verifiering: `not_evaluated`", report)

    def test_validation_never_alters_the_solver_artifacts(self) -> None:
        run, directory = self._run()
        before = {name: (directory / name).read_bytes() for name in ("joint_input.json", "joint_result.json", "joint_manifest.json")}
        write_validation(directory, processed_dir=self.dir, config_path=self.scenario, catalog_path=CATALOG)
        after = {name: (directory / name).read_bytes() for name in before}
        self.assertEqual(before, after)

    def test_validation_can_run_separately_without_rerunning_the_optimizer(self) -> None:
        _run, directory = self._run()
        payload = validate_run(directory, processed_dir=self.dir, config_path=self.scenario, catalog_path=CATALOG)
        rules = {item["rule_id"]: item["status"] for item in payload["rules"]}
        self.assertEqual(rules["dataset_hash"], "pass")
        self.assertEqual(rules["config_hash"], "pass")
        self.assertEqual(rules["catalog_hash"], "pass")
        self.assertEqual(rules["manifest_hashes"], "pass")

    def test_a_changed_dataset_or_config_is_detected(self) -> None:
        _run, directory = self._run()
        (self.dir / "demand_scope.csv").write_text("activity_id,scope_status\nact-X,included\n", encoding="utf-8")
        self.scenario.write_text(PAIR_SCENARIO + "\n", encoding="utf-8")
        rules = {item["rule_id"]: item["status"] for item in
                 validate_run(directory, processed_dir=self.dir, config_path=self.scenario, catalog_path=CATALOG)["rules"]}
        self.assertEqual(rules["dataset_hash"], "fail")
        self.assertEqual(rules["config_hash"], "fail")

    def test_a_corrupted_saved_result_is_caught_without_the_optimizer(self) -> None:
        _run, directory = self._run()
        path = directory / "joint_result.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        result["assignments"][0]["participants"] -= 1  # lose one participant
        path.write_text(json.dumps(result), encoding="utf-8")
        failing = {item["rule_id"] for item in validate_run(directory)["rules"] if item["status"] == "fail"}
        self.assertTrue({"manifest_hashes", "participants_placed"} <= failing)

    def test_a_consistently_rewritten_manifest_still_exposes_a_technical_fault(self) -> None:
        import hashlib
        _run, directory = self._run()
        path = directory / "joint_result.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        result["staff_pool_size"] = 0
        path.write_text(json.dumps(result), encoding="utf-8")
        manifest_path = directory / "joint_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["result_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        payload = validate_run(directory)
        failing = {item["rule_id"] for item in payload["rules"] if item["status"] == "fail"}
        self.assertNotIn("manifest_hashes", failing)
        self.assertIn("staff_pool_covers_peak", failing)
        self.assertFalse(payload["summary"]["technically_validated"])


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.scenario = _write_pair_dataset(self.dir)
        self.runs = self.dir / "runs"

    def _main(self, *args: str) -> tuple[int, dict]:
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main([*args, "--processed-dir", str(self.dir), "--runs-dir", str(self.runs)])
        return code, json.loads(stdout.getvalue())

    def test_optimize_joint_reports_validation_and_validate_joint_run_repeats_it(self) -> None:
        code, payload = self._main("optimize-joint", "--config", str(self.scenario))
        self.assertEqual((code, payload["status"]), (0, "ok"))
        self.assertEqual(payload["run"]["validation"]["technical_validation"], "pass")
        run_id = payload["run"]["run_id"]
        code, again = self._main("validate-joint-run", "--run-id", run_id, "--config", str(self.scenario))
        self.assertEqual((code, again["status"]), (0, "ok"))
        rules = {item["rule_id"]: item["status"] for item in again["validation"]["rules"]}
        self.assertEqual(rules["dataset_hash"], "pass")
        self.assertEqual(rules["config_hash"], "pass")

    def test_technical_fault_is_reported_with_its_own_status_and_exit_code(self) -> None:
        _code, payload = self._main("optimize-joint", "--config", str(self.scenario))
        run_id = payload["run"]["run_id"]
        path = self.runs / run_id / "joint_result.json"
        original = path.read_text(encoding="utf-8")
        result = json.loads(original)
        result["costs"]["annual_room_cost_ore"] += 1
        path.write_text(json.dumps(result), encoding="utf-8")
        code, again = self._main("validate-joint-run", "--run-id", run_id)
        self.assertEqual((code, again["status"]), (3, "technical_validation_failed"))
        self.assertEqual(again["validation"]["summary"]["technical_validation"], "fail")
        # The solver outcome itself is preserved for troubleshooting.
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["solver"]["outcome"], "optimal")


@unittest.skipUnless((PROCESSED / "optimization_demands.csv").is_file(), "kräver lokalt genererat underlag (data/processed)")
class RealSubsetRegressionTests(unittest.TestCase):
    """The real 12-exam run from PR #7, with every rule's real status."""

    EXPECTED_TECHNICAL_NOT_APPLICABLE = {"non_room_demands", "fixed_exams_keep_history"}
    EXPECTED_BUSINESS = {
        "calendar_rules_verified": "not_evaluated", "room_rules_verified": "not_evaluated",
        "staffing_rules_verified": "not_evaluated", "cost_basis_verified": "not_evaluated",
        "demand_basis_verified": "not_evaluated", "population_completeness": "not_evaluated",
        "student_overlap": "not_evaluated", "digital_compatibility_verified": "not_evaluated",
        "group_disjointness": "not_evaluated", "unsupported_parameters": "not_evaluated",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.record = run_real_subset(SUBSET, PROCESSED, CATALOG, Path(cls.temp.name))
        cls.directory = Path(cls.temp.name) / cls.record["run_id"]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def _rules(self, **kwargs) -> dict[str, dict]:
        payload = validate_run(self.directory, processed_dir=PROCESSED, config_path=SUBSET, catalog_path=CATALOG, **kwargs)
        return {item["rule_id"]: item for item in payload["rules"]}

    def test_real_run_statuses_rule_by_rule(self) -> None:
        rules = self._rules()
        for rule_id, item in rules.items():
            if item["axis"] == "technical":
                expected = "not_applicable" if rule_id in self.EXPECTED_TECHNICAL_NOT_APPLICABLE else "pass"
                self.assertEqual(item["status"], expected, f"{rule_id}: {item['reason']}")
        for rule_id, status in self.EXPECTED_BUSINESS.items():
            self.assertEqual(rules[rule_id]["status"], status, rule_id)
        for rule_id in ("manifest_hashes", "schema_versions", "result_belongs_to_input", "dataset_hash", "config_hash", "catalog_hash"):
            self.assertEqual(rules[rule_id]["status"], "pass", rule_id)

    def test_real_run_numbers_are_recomputed_independently(self) -> None:
        result = json.loads((self.directory / "joint_result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["solver"]["outcome"], "optimal")
        self.assertEqual(result["costs"]["comparable_total_cost_ore"], 37_900_000)
        self.assertEqual((result["staff_pool_size"], result["changed_exam_demands"]), (3, 4))
        rules = self._rules()
        self.assertIn("Poolen 3 täcker maximal samtidig bemanning 3", rules["staff_pool_covers_peak"]["reason"])
        self.assertIn("37900000", rules["costs_recomputed"]["reason"])
        self.assertIn("4 flyttade", rules["changed_exams_recomputed"]["reason"])
        self.assertIn("266", rules["scope_disclosed"]["reason"])
        self.assertIn("266", rules["population_completeness"]["reason"])

    def test_raw_source_hashes_are_unchanged(self) -> None:
        source_dir, manifest = default_source_dir(), REPO_ROOT / "reports" / "run_manifest.json"
        if not Path(source_dir).is_dir() or not manifest.is_file():
            self.skipTest("originalunderlag eller källmanifest saknas lokalt")
        self.assertEqual(self._rules(source_dir=source_dir, source_manifest=manifest)["source_data_hashes"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
