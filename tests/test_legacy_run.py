"""A run saved before the model counted in kronor (amounts in öre) is still read and eftervaliderad, and never rewritten."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from joint_validation_cases import copy_case, write_run  # noqa: E402
from tentaoptimering.joint_contract import read_problem  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402

_KR = re.compile(r"(?<=[a-z0-9])_kr(?![a-z0-9])")


def to_legacy(document):
    """The same document as an older version of the program wrote it: `_ore` keys and whole öre."""
    if isinstance(document, list):
        return [to_legacy(item) for item in document]
    if not isinstance(document, dict):
        return document
    legacy_row = isinstance(document.get("parameter_id"), str) and bool(_KR.search(document["parameter_id"]))
    out = {}
    for key, value in document.items():
        scalar = not isinstance(value, (dict, list))
        if _KR.search(key):
            out[_KR.sub("_ore", key)] = round(value * 100) if scalar and isinstance(value, (int, float)) and not isinstance(value, bool) else to_legacy(value)
        elif legacy_row and key == "parameter_id":
            out[key] = _KR.sub("_ore", value)
        elif legacy_row and key == "value" and isinstance(value, (int, float)) and not isinstance(value, bool):
            out[key] = round(value * 100)
        else:
            out[key] = to_legacy(value)
    return out


class LegacyRunTests(unittest.TestCase):
    def _statuses(self, run: Path) -> dict[str, str]:
        return {item["rule_id"]: item["status"] for item in validate_run(run)["rules"]}

    def test_an_old_run_gets_the_same_verdicts_as_the_same_run_in_kronor(self) -> None:
        problem, result = copy_case()
        legacy_problem, legacy_result = to_legacy(problem), to_legacy(result)
        self.assertIn("annual_fixed_cost_ore", json.dumps(legacy_problem))  # the fixture really is in the old format
        with tempfile.TemporaryDirectory() as temp:
            new_run = write_run(Path(temp) / "new", problem, result)
            old_run = write_run(Path(temp) / "old", legacy_problem, legacy_result)
            before = (old_run / "joint_input.json").read_bytes()
            self.assertEqual(self._statuses(old_run), self._statuses(new_run))
            self.assertEqual(self._statuses(old_run)["costs_recomputed"], "pass")
            self.assertEqual((old_run / "joint_input.json").read_bytes(), before)  # the stored file is never rewritten

    def test_a_wrong_cost_in_an_old_run_is_still_caught(self) -> None:
        problem, result = copy_case()
        legacy_result = to_legacy(result)
        legacy_result["costs"]["comparable_total_cost_ore"] += 100  # one krona too much
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self._statuses(write_run(Path(temp) / "old", to_legacy(problem), legacy_result))["costs_recomputed"], "fail")

    def test_the_engine_reads_an_old_input_file_as_kronor(self) -> None:
        problem, _ = copy_case()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "joint_input.json"
            path.write_text(json.dumps(to_legacy(problem)), encoding="utf-8")
            loaded = read_problem(path)
            self.assertEqual({room.room_id: room.annual_fixed_cost_kr for room in loaded.rooms}, {"R1": 100, "R2": 60})
            self.assertEqual((loaded.staffing.annual_cost_kr_per_staff, loaded.staffing.cost_kr_per_staff_session), (10, 1))


if __name__ == "__main__":
    unittest.main()
