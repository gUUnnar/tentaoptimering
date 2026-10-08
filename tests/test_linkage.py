from __future__ import annotations

import unittest

import pandas as pd

from tentaoptimering.linkage import candidate_linkage, extract_course_codes


class CandidateLinkageTests(unittest.TestCase):
    def test_extract_course_codes_handles_a_co_exam_cell(self) -> None:
        self.assertEqual(extract_course_codes(" abc123, DEF456 "), ["ABC123", "DEF456"])

    def test_candidate_linkage_keeps_ambiguity_visible(self) -> None:
        bookings = pd.DataFrame(
            {
                "placement_id": ["placement-1", "placement-2"],
                "exam_order_id": ["order-1", "order-2"],
                "course_codes": ["ABC123, DEF456", "GHI789"],
                "scheduled_date": ["2026-01-12", "2026-01-12"],
                "scheduled_time": ["08:00-12:00", "14:00-16:00"],
                "location_key": ["room-1", "room-2"],
            }
        )
        ladok = pd.DataFrame(
            {
                "activity_id": ["ladok-1", "ladok-2", "ladok-3"],
                "course_code": ["ABC123", "DEF456", "DEF456"],
                "start_date": ["2026-01-12"] * 3,
                "start_time": ["08:00"] * 3,
                "location_key": ["room-1", "room-3", "room-4"],
            }
        )

        result = candidate_linkage(bookings, ladok)

        self.assertEqual(result.metrics["booking_course_placement_rows_eligible"], 3)
        self.assertEqual(result.metrics["booking_placement_rows_without_extractable_course_code"], 0)
        self.assertEqual(result.metrics["booking_course_placement_rows_single_candidate"], 1)
        self.assertEqual(result.metrics["booking_course_placement_rows_ambiguous_candidates"], 1)
        self.assertEqual(result.metrics["booking_course_placement_rows_no_candidate"], 1)
        self.assertEqual(
            result.metrics["booking_course_placement_rows_eligible"],
            result.metrics["booking_course_placement_rows_single_candidate"]
            + result.metrics["booking_course_placement_rows_ambiguous_candidates"]
            + result.metrics["booking_course_placement_rows_no_candidate"],
        )
        statuses = result.candidate_links.groupby("course_code")["candidate_status"].first().to_dict()
        self.assertEqual(statuses["ABC123"], "single_candidate")
        self.assertEqual(statuses["DEF456"], "ambiguous_candidates")
        self.assertEqual(statuses["GHI789"], "no_candidate")


if __name__ == "__main__":
    unittest.main()
