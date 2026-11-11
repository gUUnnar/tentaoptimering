"""The Ladok occasion list is measured against bookings and the existing extract; it never becomes demand by itself."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tentaoptimering.ladok_occasions import COLUMNS, HEADER_ROW, load_occasions, reconcile  # noqa: E402


def _write(path: Path, rows: list[list[object]]) -> None:
    header = ["Status", "Aktivitetstillfällesnamn", "Datum", "Ort", "Lokal", "Antal platser", "Antal anmälda", "Kurskod", "Kurs", "Kurstillfälle",
              "Avser modul", "Anmälningsperiod", "Anonymt", "Prefix", "Ansvarig", "Typ", "Senast ändrad", "Övrig information", "Inställd"]
    top = [["Aktivitetstillfällen"], ["Tidpunkt för export", "2026-10-21 07:11"], ["Datum", "2026-01-01 - 2026-07-31"], ["Sorteringsordning", "datum"], []]
    frame = pd.DataFrame(top + [header] + rows)
    frame.to_excel(path, header=False, index=False)


class OccasionTests(unittest.TestCase):
    def test_load_drops_repeated_headers_and_reconcile_counts_matches_by_prefix_and_date(self) -> None:
        self.assertEqual(HEADER_ROW, 5)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ladok.xlsx"
            row = lambda status, day, count, code, prefix: [status, "Tenta", f"{day} 08:00", "Uppsala", None, None, count, code, "Kurs", None, None, None, "Ja", prefix, "X", "Omtentamen", None, None, None]  # noqa: E731
            _write(path, [row("Publicerat", "2026-04-07", 40, "AAA111", "PFX01"), row("Publicerat", "2026-04-08", None, "BBB222", None),
                          row("Status", "2026-04-09", 5, "CCC333", "PFX03"), row("Utkast", "2026-01-12", 71, "1DL321", "PFX04")])
            occasions = load_occasions(path)
            self.assertEqual(len(occasions), 3)  # the repeated header row is dropped
            self.assertEqual(occasions.attrs["rows_dropped"], 1)
            bookings = pd.DataFrame({"prefix": ["PFX01", "ZZZ99", "PFX04"], "scheduled_date": ["2026-04-07", "2026-04-07", "2026-01-12"]})
            existing = pd.DataFrame({"course_code": ["1DL321"], "start_date": ["2026-01-12 00:00"], "start_time": ["08:00:00"], "registered_count": [71]})
            result = reconcile(occasions, bookings, existing)
            self.assertEqual(result["occasions"], 3)
            self.assertEqual(result["occasions_without_prefix"], 1)
            self.assertEqual(result["occasions_without_registered"], 1)
            self.assertEqual(result["booked_exam_days_by_month"]["2026-04"], {"booked_exam_days": 2, "matched_by_prefix_and_date": 1})
            self.assertEqual(result["booked_exam_days_by_month"]["2026-01"], {"booked_exam_days": 1, "matched_by_prefix_and_date": 1})
            self.assertEqual((result["existing_extract"]["joined_on_course_date_time"], result["existing_extract"]["registered_equal"]), (1, 1))
            self.assertEqual(len(COLUMNS), 19)


if __name__ == "__main__":
    unittest.main()
