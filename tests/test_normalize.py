from __future__ import annotations

import unittest

import pandas as pd

from tentaoptimering.normalize import key_text, normalize_bookings, normalize_ladok
from tentaoptimering.validation import validate_bookings


class NormalizeTests(unittest.TestCase):
    def test_ladok_mojibake_is_repaired_before_keys_are_built(self) -> None:
        frame = pd.DataFrame({
            "course_code": ["3Ã–N002"], "name_sv": ["RÃ¥byvÃ¤gen"],
            "start_date": ["2026-02-28"], "start_time": ["08:00"],
            "activity_type": ["Tentamen"], "location": ["RÃ¥byvÃ¤gen 95"],
            "registration_flag": [1], "total_count": [8], "registered_count": [8],
            "cancelled_count": [0], "added_count": [0], "re_registered_or_early_term_count": [0],
        })

        result = normalize_ladok(frame)

        self.assertEqual(result.loc[0, "course_code"], "3ÖN002")
        self.assertEqual(result.loc[0, "location_key"], "råbyvägen-95")
    def test_key_text_normalizes_spaces_and_punctuation(self) -> None:
        self.assertEqual(key_text("  Bergsbrunnagatan 15, Sal 1 "), "bergsbrunnagatan-15-sal-1")

    def test_repeated_prefix_is_reported_as_mixed_grain(self) -> None:
        columns = {
            "org_code": [1, 1],
            "course_codes": ["ABC", "ABC"],
            "prefix": ["P1", "P1"],
            "status": ["Klar", "Klar"],
            "course_name": ["Kurs", "Kurs"],
            "co_exam": ["Nej", "Nej"],
            "co_exam_identical": ["Nej", "Nej"],
            "co_exam_comment": [None, None],
            "scheduled_date": ["2026-01-01", "2026-01-01"],
            "weekday": ["tor", "tor"],
            "scheduled_time": ["08:00-12:00", "08:00-12:00"],
            "duration": ["4:00", "4:00"],
            "day_part": ["fm", "fm"],
            "address": ["Adress", "Adress"],
            "room": ["Sal 1", "Sal 2"],
            "booked_places": [10, 20],
            "candidate_count": [30, 30],
            "original_candidate_count": [30, 30],
            "re_exam_candidates": [0, 0],
            "support_candidates": [0, 0],
            "support_placed": [0, 0],
            "requested_date": ["2026-01-01", "2026-01-01"],
            "reserve_date_1": [None, None],
            "reserve_date_2": [None, None],
            "no_reserve_date_reason": [None, None],
            "exam_type": ["Ordinarie", "Ordinarie"],
            "digital_exam": ["Nej", "Nej"],
            "exam_name": ["Prov", "Prov"],
            "city": ["Uppsala", "Uppsala"],
            "transport": ["Nej", "Nej"],
            "transport_comment": [None, None],
            "depot": [None, None],
            "coordination_comment": [None, None],
            "institution_comment": [None, None],
            "raindance_project": [123, 123],
        }
        normalized = normalize_bookings(pd.DataFrame(columns))
        quality = validate_bookings(normalized)
        self.assertEqual(quality.metrics["unique_non_missing_prefixes"], 1)
        self.assertEqual(quality.metrics["repeated_non_missing_prefixes"], 1)
        self.assertEqual(normalized["placement_id"].nunique(), 2)


if __name__ == "__main__":
    unittest.main()
