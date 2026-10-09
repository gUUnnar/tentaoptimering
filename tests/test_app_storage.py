from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from tentaoptimering.app_storage import AppStorage, dump_toml


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
