from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tentaoptimering.app_storage import AppStorage


class AppStorageTest(unittest.TestCase):
    def test_storage_creates_its_directories_and_keeps_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            storage = AppStorage(Path(temporary))
            for directory in (storage.runs_dir, storage.snapshots_dir, storage.processed_dir, storage.reports_dir):
                self.assertTrue(directory.is_dir())
            self.assertEqual(storage.settings(), {"source_dir": None})
            self.assertEqual(storage.save_settings(temporary), {"source_dir": temporary})
            self.assertEqual(AppStorage(Path(temporary)).settings(), {"source_dir": temporary})
            with self.assertRaises(ValueError):
                storage.save_settings(str(Path(temporary) / "saknas"))

    def test_run_ids_cannot_point_outside_the_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            storage = AppStorage(Path(temporary))
            self.assertEqual(storage.run_directory("kord-1"), (storage.runs_dir / "kord-1").resolve())
            for run_id in ("../outside", "..\\outside", "/outside", ".hidden"):
                with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                    storage.run_directory(run_id)
                with self.assertRaises(ValueError):
                    storage.warm_start(run_id)

    def test_warm_start_decision_is_none_for_a_run_without_one(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            storage = AppStorage(Path(temporary))
            (storage.runs_dir / "kord-1").mkdir()
            self.assertIsNone(storage.warm_start("kord-1"))
            self.assertEqual(storage.warm_start_candidates(), [])


if __name__ == "__main__":
    unittest.main()
