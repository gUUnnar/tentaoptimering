from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO_ROOT / "tools" / "check_code_file_lengths.py"
SPEC = importlib.util.spec_from_file_location("check_code_file_lengths", CHECKER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Kunde inte läsa filstorlekskontrollen: {CHECKER_PATH}")
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


class CodeFilePolicyTests(unittest.TestCase):
    def test_no_python_file_reaches_mandatory_split_limit(self) -> None:
        errors = [item for item in checker.check(REPO_ROOT) if item.level == "ERROR"]
        self.assertEqual(errors, [], f"Dela upp överstora Python-filer: {errors}")

    def test_thresholds_are_explicit(self) -> None:
        path = Path("example.py")
        self.assertEqual(checker.assess(path, 500).level, "OK")
        self.assertEqual(checker.assess(path, 501).level, "NOTICE")
        self.assertEqual(checker.assess(path, 800).level, "STRONG WARNING")
        self.assertEqual(checker.assess(path, 1000).level, "ERROR")


if __name__ == "__main__":
    unittest.main()
