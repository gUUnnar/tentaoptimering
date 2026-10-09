from __future__ import annotations

import tempfile
import tomllib
import unittest
from copy import deepcopy
from pathlib import Path

from tentaoptimering.app_storage import AppStorage, dump_toml
from tentaoptimering.integrated_config import load_integrated_term_scenario
from tentaoptimering.term_calendar import generate_calendar_slots


class AppStorageTest(unittest.TestCase):
    def test_toml_writer_preserves_nested_scenario_shape(self) -> None:
        content = {
            "scenario_id": "demo",
            "calendar": {"allowed_weekdays": [1, 2], "passes": [{"pass_id": "day", "start_time": "08:00"}]},
            "assumption": [{"id": "known", "value": "1", "status": "provisional"}],
        }
        self.assertEqual(tomllib.loads(dump_toml(content)), content)

    def test_user_copy_is_editable_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            storage = AppStorage(Path(temporary))
            copied = storage.create_scenario("ui-test")
            self.assertTrue(copied["editable"])
            self.assertEqual(copied["engine"], "integrated_term")
            self.assertTrue(storage.validate_scenario("ui-test")["valid"])

    def test_invalid_update_preserves_valid_scenario_and_run_ids_are_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            storage = AppStorage(Path(temporary))
            before = storage.create_scenario("safe-copy")["content"]
            invalid = deepcopy(before)
            del invalid["calendar"]["passes"]
            with self.assertRaises(ValueError):
                storage.update_scenario("safe-copy", invalid)
            self.assertEqual(storage.scenario("safe-copy")["content"], before)
            snapshot = storage.create_run_snapshot("safe-copy")
            changed = deepcopy(before)
            changed["calendar"]["turnaround_minutes"] = 15
            storage.update_scenario("safe-copy", changed)
            self.assertEqual(tomllib.loads(Path(snapshot["path"]).read_text(encoding="utf-8")), before)
            for run_id in ("../outside", "..\\outside", "/outside"):
                with self.assertRaises(ValueError):
                    storage.run(run_id)

    def test_saved_controls_synchronize_assumptions_and_calendar_period(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            storage = AppStorage(Path(temporary))
            content = storage.create_scenario("synchronized")["content"]
            content["calendar"]["start_date"] = "2026-02-01"
            content["calendar"]["end_date"] = "2026-02-28"
            content["calendar"]["turnaround_minutes"] = 15
            content["staffing"]["minimum_break_minutes"] = 20
            storage.update_scenario("synchronized", content)
            saved = storage.scenario("synchronized")["content"]
            assumptions = {item["id"]: item["value"] for item in saved["assumption"]}
            self.assertEqual(assumptions["room_turnaround"], "15")
            self.assertIn("break 20 min", assumptions["individual_staffing_rules"])
            self.assertEqual(saved["calendar"]["period"][0]["start_date"], "2026-02-01")
            self.assertEqual(saved["calendar"]["period"][0]["end_date"], "2026-02-28")
            scenario = load_integrated_term_scenario(storage.scenario_path("synchronized"))
            slots = generate_calendar_slots(scenario.calendar)
            self.assertTrue(slots)
            self.assertGreaterEqual(min(item.scheduled_date.isoformat() for item in slots), "2026-02-01")
            self.assertLessEqual(max(item.scheduled_date.isoformat() for item in slots), "2026-02-28")
