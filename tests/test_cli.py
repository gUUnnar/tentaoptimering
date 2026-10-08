from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tentaoptimering.cli import build_parser, main
from tentaoptimering.paths import REPO_ROOT


class CliTests(unittest.TestCase):
    def test_json_is_default_for_prepare(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.command, "prepare")
        self.assertEqual(args.output_format, "json")

    def test_status_returns_structured_readiness(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report_dir = root / "reports"
            report_dir.mkdir()
            (report_dir / "optimization_readiness.json").write_text(
                json.dumps(
                    {
                        "metrics": {
                            "capacity_optimization_readiness": "blocked_test",
                            "rooms_with_verified_capacity": 0,
                            "ladok_activities_ambiguous_candidates": 2,
                            "optimization_demands_missing_configured_value": 1,
                        }
                    }
                ),
                encoding="utf-8",
            )
            (report_dir / "run_manifest.json").write_text(
                json.dumps({"schema_version": 1, "sources": {}, "artifacts": {}}),
                encoding="utf-8",
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "status",
                        "--report-dir",
                        str(report_dir),
                        "--processed-dir",
                        str(root / "processed"),
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["optimization_readiness"]["state"], "blocked_test")
        self.assertEqual(len(payload["warnings"]), 3)

    def test_missing_status_artifacts_return_structured_error(self) -> None:
        with TemporaryDirectory() as directory:
            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = main(["status", "--report-dir", directory])

        payload = json.loads(stderr.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["type"], "FileNotFoundError")

    def test_validate_config_returns_normalized_json(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "validate-config",
                    "--config",
                    str(REPO_ROOT / "config" / "scenarios" / "reference.toml"),
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["config"]["scenario_id"], "reference_fixed_time")

    def test_optimize_requires_explicit_config(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["optimize"])

        payload = json.loads(stderr.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["status"], "error")
        self.assertIn("--config", payload["error"]["message"])

    def test_optimize_term_requires_explicit_config(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["optimize-term"])

        payload = json.loads(stderr.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertIn("--config", payload["error"]["message"])


if __name__ == "__main__":
    unittest.main()
