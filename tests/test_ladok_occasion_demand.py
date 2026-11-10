"""Demand after the Ladok extract's last date comes from the occasion list, marked as its own source; earlier dates keep the extract."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_ladok_occasions import _write  # noqa: E402
from tentaoptimering.ladok_occasions import EXTRACT_SOURCE, OCCASION_SOURCE, load_occasions, to_activities  # noqa: E402
from tentaoptimering.model_inputs import _build_candidate_relations  # noqa: E402
from tentaoptimering.paths import SourceFiles  # noqa: E402
from tentaoptimering.pipeline import _with_occasion_demand  # noqa: E402
from tentaoptimering.normalize import normalize_ladok  # noqa: E402

ROW = lambda status, day, count, code, typ="Ordinarie tentamen", ort="Uppsala", lokal="Bergsbrunnagatan 15 Sal 1": [  # noqa: E731
    status, "Tenta", f"{day} 08:00", ort, lokal, None, count, code, "Kurs", None, None, None, "Ja", "PFX01", "X", typ, None, None, None]


def _occasions(rows: list[list[object]]) -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "ladok.xlsx"
        _write(path, rows)
        return load_occasions(path)


class ToActivitiesTests(unittest.TestCase):
    def test_only_later_exam_dates_with_a_course_become_activities_and_a_missing_count_stays_empty(self) -> None:
        occasions = _occasions([
            ROW("Publicerat", "2026-03-31", 10, "AAA111"),   # the extract's last date: not used
            ROW("Publicerat", "2026-04-01", 40, "BBB222"),
            ROW("Publicerat", "2026-04-02", None, "CCC333", "Omtentamen"),
            ROW("Publicerat", "2026-04-03", 5, "DDD444", "PM"),   # not an exam in a room
        ])
        activities = to_activities(occasions, "2026-03-31")
        self.assertEqual(activities["course_code"].tolist(), ["BBB222", "CCC333"])
        self.assertEqual(activities["registered_count"].isna().tolist(), [False, True])  # unknown, never zero
        self.assertEqual(activities["location"].iloc[0], "Uppsala, Bergsbrunnagatan 15 Sal 1")
        self.assertEqual(activities["start_time"].iloc[0], "08:00")
        self.assertEqual(len(to_activities(occasions, None)), 3)  # without a limit every exam occasion counts


class PipelineStepTests(unittest.TestCase):
    def _extract(self) -> pd.DataFrame:
        raw = pd.DataFrame({"course_code": ["AAA111"], "name_sv": ["A"], "start_date": ["2026-03-31"], "start_time": ["08:00"], "activity_type": ["Ordinarie tentamen"],
                            "location": ["X"], "registration_flag": [1], "total_count": [12], "registered_count": [10], "cancelled_count": [2],
                            "added_count": [None], "re_registered_or_early_term_count": [None]})
        frame = normalize_ladok(raw)
        frame["demand_source"] = EXTRACT_SOURCE
        return frame

    def test_without_the_file_the_extract_is_returned_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            frame = self._extract()
            self.assertTrue(_with_occasion_demand(frame, SourceFiles(source_dir=Path(temp))).equals(frame))

    def test_later_occasions_are_added_with_their_own_ids_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            sources = SourceFiles(source_dir=Path(temp))
            _write(sources.ladok_occasions, [ROW("Publicerat", "2026-03-31", 99, "AAA111"), ROW("Publicerat", "2026-04-07", 40, "BBB222")])
            result = _with_occasion_demand(self._extract(), sources)
            self.assertEqual(result["activity_id"].tolist(), ["ladok-000001", "occ-000001"])
            self.assertEqual(result["demand_source"].tolist(), [EXTRACT_SOURCE, OCCASION_SOURCE])
            self.assertEqual(int(result.loc[0, "registered_count"]), 10)  # the extract keeps its date and its count
            self.assertEqual(int(result.loc[1, "registered_count"]), 40)


class RelationTests(unittest.TestCase):
    def test_the_source_follows_the_activity_into_the_candidate_relation(self) -> None:
        ladok = pd.DataFrame({"activity_id": ["occ-000001"], "course_code": ["BBB222"], "start_date": ["2026-04-07"], "start_time": ["08:00"],
                              "registered_count": [40], "demand_source": [OCCASION_SOURCE]})
        events = pd.DataFrame({"exam_event_id": ["e1"], "course_code": ["BBB222"], "scheduled_date": ["2026-04-07"], "booking_start_time": ["08:00"]})
        relation = _build_candidate_relations(ladok, events, "registered_count")
        self.assertEqual(relation["relationship_status"].tolist(), ["unambiguous_candidate"])
        self.assertEqual(relation["demand_input_status"].tolist(), ["ready_provisional_ladok_demand"])
        self.assertEqual(relation["demand_source"].tolist(), [OCCASION_SOURCE])


if __name__ == "__main__":
    unittest.main()
