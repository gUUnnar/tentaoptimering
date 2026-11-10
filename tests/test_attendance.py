"""Reported attendance as its own data grain: normalisation, quality counts, summaries and the optional source file.

Hand-worked: two ordinary exams (60 of 100 and 50 of 50 places) and one retake (10 of 40) give 120 of 190 places overall; an exact
duplicate row is removed and counted, a row above its places is kept and flagged, and a missing value is never turned into zero.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tentaoptimering.attendance import ATTENDANCE_FILE, attendance_summary, load_attendance, normalize_attendance  # noqa: E402
from tentaoptimering.attendance_api import attendance_payload  # noqa: E402
from tentaoptimering.paths import SourceFiles  # noqa: E402
from tentaoptimering.underlay_sources import inspect_source_dir  # noqa: E402


def _raw() -> pd.DataFrame:
    rows = [
        {"Kurskoder": "AAA", "Status": "Klar", "Kursnamn": "A", "Inbokat datum": "2026-01-12", "Inbokad tid": "08:00-13:00", "FM/EM": "FM",
         "Skrivsal": "Fyrishov", "Typ av tenta": "Ordinarie tenta", "Justerat tot skrivplatser": 100, "Närvaro": 60, "Frånvaro": 40},
        {"Kurskoder": "BBB", "Status": "Klar", "Kursnamn": "B", "Inbokat datum": "2026-01-13", "Inbokad tid": "08:00-13:00", "FM/EM": "FM",
         "Skrivsal": "Bergsbrunnagatan 15", "Typ av tenta": "Ordinarie tenta", "Justerat tot skrivplatser": 50, "Närvaro": 55, "Frånvaro": 0},
        {"Kurskoder": "CCC", "Status": "Klar", "Kursnamn": "C", "Inbokat datum": "2026-06-02", "Inbokad tid": "08:00-13:00", "FM/EM": "FM",
         "Skrivsal": "Klostergatan 3", "Typ av tenta": "Omtenta", "Justerat tot skrivplatser": 40, "Närvaro": 10, "Frånvaro": 30},
        {"Kurskoder": "DDD", "Status": "2026-03-04", "Kursnamn": "D", "Inbokat datum": "2026-06-03", "Inbokad tid": None, "FM/EM": "EM",
         "Skrivsal": None, "Typ av tenta": "Omtenta", "Justerat tot skrivplatser": 30, "Närvaro": None, "Frånvaro": None},
    ]
    frame = pd.DataFrame(rows)
    return pd.concat([frame, frame.iloc[[0]]], ignore_index=True)  # an exact duplicate of the first row


class NormalizeTests(unittest.TestCase):
    def test_duplicates_are_removed_and_the_quality_record_counts_what_is_odd(self) -> None:
        frame, quality = normalize_attendance(_raw())
        self.assertEqual((quality["rows_read"], quality["duplicate_rows_removed"], quality["rows"]), (5, 1, 4))
        self.assertEqual(quality["rows_attendance_above_adjusted_places"], 1)
        self.assertEqual(quality["rows_with_date_in_status"], 1)
        self.assertEqual(quality["rows_without_attendance"], 1)
        self.assertEqual((quality["first_date"], quality["last_date"]), ("2026-01-12", "2026-06-03"))
        self.assertTrue(frame.loc[frame.course_code == "AAA", "at_fyrishov"].item())
        self.assertTrue(pd.isna(frame.loc[frame.course_code == "DDD", "attendance"]).item())  # unknown, not zero

    def test_the_summary_excludes_unknowns_and_keeps_rows_above_places(self) -> None:
        frame, _ = normalize_attendance(_raw())
        summary = attendance_summary(frame)
        self.assertEqual((summary["total"]["attendance"], summary["total"]["adjusted_places"]), (125, 190))  # 60 + 55 + 10 of 100 + 50 + 40
        self.assertEqual(summary["total"]["rows_above_places"], 1)
        self.assertEqual(summary["rows_unusable"], 1)
        self.assertEqual((summary["at_fyrishov"]["attendance"], summary["at_fyrishov"]["adjusted_places"]), (60, 100))
        january = {row["exam_type"]: row for row in summary["by_month_and_type"] if row["month"] == "2026-01"}
        self.assertAlmostEqual(january["Ordinarie tenta"]["share"], 115 / 150, places=4)
        june = {row["exam_type"]: row for row in summary["by_month_and_type"] if row["month"] == "2026-06"}
        self.assertAlmostEqual(june["Omtenta"]["share"], 0.25, places=4)


class SourceTests(unittest.TestCase):
    def test_the_file_loads_from_excel_and_is_an_optional_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            sources = SourceFiles(source_dir=folder)
            with pd.ExcelWriter(sources.attendance) as writer:
                _raw().to_excel(writer, sheet_name="Tentor", index=False)
            frame, quality = normalize_attendance(load_attendance(sources.attendance))
            self.assertEqual(quality["rows"], 4)
            self.assertEqual(len(frame), 4)
            facts = inspect_source_dir(folder)
            optional = facts["optional_files"]
            self.assertNotIn("attendance", [item["role"] for item in facts["files"]])
            self.assertEqual([item["role"] for item in optional], ["attendance", "ladok_occasions"])
            self.assertTrue(optional[0]["found"])
            self.assertFalse(optional[1]["found"])
            self.assertFalse(facts["ready"])  # the required sources are still missing; the optional one never makes it ready
            self.assertNotIn("attendance", [role for role, _label, _path in sources.roles()])

    def test_the_route_payload_says_when_no_attendance_is_prepared(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            payload = attendance_payload(Path(temp))
            self.assertFalse(payload["available"])
            frame, quality = normalize_attendance(_raw())
            frame.to_csv(Path(temp) / ATTENDANCE_FILE, index=False, encoding="utf-8-sig")
            payload = attendance_payload(Path(temp))
            self.assertTrue(payload["available"])
            self.assertEqual(payload["kind"], "observed_attendance")
            self.assertEqual(payload["summary"]["total"]["adjusted_places"], 190)


if __name__ == "__main__":
    unittest.main()
