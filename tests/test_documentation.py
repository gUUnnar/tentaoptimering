from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO_ROOT / "tools" / "check_documentation.py"
SPEC = importlib.util.spec_from_file_location("check_documentation", CHECKER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Kunde inte läsa dokumentationskontrollen: {CHECKER_PATH}")
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


class DocumentationTests(unittest.TestCase):
    def test_documentation_structure_and_links(self) -> None:
        issues = checker.check(REPO_ROOT)
        self.assertEqual(issues, [], f"Rätta dokumentationen: {issues}")

    def test_retired_paths_are_explicit(self) -> None:
        retired = set(checker.RETIRED_PATHS)
        self.assertIn("docs/KRAVUPPFYLLNAD.md", retired)
        self.assertIn("docs/prototyp/index.html", retired)


if __name__ == "__main__":
    unittest.main()
