"""The booking data quality layer on synthetic extracts: complete, address-level, mixed and defective data.

The same code must give the right description for every extract (the test matrix S-A..S-F of docs/ARKITEKTURPRINCIPER_DATAKVALITET.md),
the four dimensions must be independent, and verified facts added to the configuration (never code) must change the classification.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from tentaoptimering.booking_quality import assess, classify, ladok_window, load_config

BASE_CONFIG = """
schema_version = "booking-data-quality-v1"
[meta]
version = "test"
[register]
file = "room_inventory.csv"
room_id = "room_id"
location_key = "location_key"
capacity = "capacity_seats"
[linkage]
file = "candidate_linkage.csv"
placement_id = "placement_id"
activity_id = "activity_id"
status = "candidate_status"
unique_values = ["single_candidate"]
ambiguous_values = ["ambiguous_candidates"]
none_values = ["no_candidate"]
[coverage.ladok]
file = "ladok_activities.csv"
date_column = "start_date"
[[status_rule]]
id = "st-cancelled"
value = "Avbokad"
class = "cancelled"
verified = true
source = "test"
[[status_rule]]
id = "st-active"
value = "Klar"
class = "active"
verified = true
source = "test"
"""
EXTRA = {
    "nonphys_unverified": '[[non_physical_rule]]\nid = "np"\naddress = "Hemma"\nverified = false\nsource = "obs"\n',
    "nonphys_verified": '[[non_physical_rule]]\nid = "np"\naddress = "Hemma"\nverified = true\nsource = "dataägare 2026-10-15"\n',
    "notaddr_verified": '[[not_an_address_rule]]\nid = "na"\naddress = "Sal utan anpassningar"\nverified = true\nsource = "dataägare"\n',
    "addrlevel_verified": '[[address_level_rule]]\nid = "al"\naddress = "Gata 2"\nverified = true\nsource = "dataägare 2026-10-15"\n',
    "addrlevel_unverified": '[[address_level_rule]]\nid = "al"\naddress = "Gata 2"\nverified = false\nsource = "hypotes"\n',
}
COLUMNS = ["placement_id", "exam_order_id", "address", "room", "location_key", "status", "scheduled_date", "scheduled_time", "booked_places"]
REGISTER = pd.DataFrame([("uu-1", "gata-1|sal-1", "100"), ("uu-2", "gata-1|sal-2", ""), ("", "gata-2", "")], columns=["room_id", "location_key", "capacity_seats"])


def rows(*items: tuple) -> pd.DataFrame:
    return pd.DataFrame(items, columns=COLUMNS)


def row(pid: str, address: str, room: str, status: str = "Klar", date: str = "2026-02-09", time: str = "08:00-12:00", places: str = "10") -> tuple:
    key = f"{address.lower().replace(' ', '-')}|{room.lower().replace(' ', '-')}" if address and room else address.lower().replace(" ", "-")
    return (pid, f"o-{pid}", address, room, key, status, date, time, places)


def cfg(*extras: str):
    folder = Path(tempfile.mkdtemp())
    path = folder / "q.toml"
    path.write_text(BASE_CONFIG + "\n".join(EXTRA[name] for name in extras), encoding="utf-8")
    return load_config(path)


LADOK = pd.DataFrame({"start_date": ["2026-01-12", "2026-03-31", ""]})


class DimensionTests(unittest.TestCase):
    def test_s_a_complete_data_is_identified_everywhere_without_findings(self) -> None:
        result = classify(rows(row("1", "Gata 1", "Sal 1"), row("2", "Gata 1", "Sal 1", places="60")), cfg(), REGISTER, None, LADOK)
        self.assertEqual(set(result["resource_identification"]), {"room_matched"})
        self.assertEqual(result["flags"].tolist(), [[], []])
        self.assertEqual(result["capacity"].tolist(), [100, 100])
        self.assertEqual(set(result["status_class"]), {"active"})

    def test_missing_room_is_a_fact_not_an_explanation(self) -> None:
        result = classify(rows(row("1", "Gata 2", "")), cfg(), REGISTER, None, LADOK)
        self.assertEqual((result["resource_identification"][0], result["flags"][0], result["declared_address_level"][0]), ("address_only", ["room_missing"], False))

    def test_s_b_address_level_only_when_a_verified_rule_declares_it(self) -> None:
        data = rows(row("1", "Gata 2", ""), row("2", "Gata 3", ""))
        declared = classify(data, cfg("addrlevel_verified"), REGISTER, None, LADOK)
        self.assertEqual(declared["declared_address_level"].tolist(), [True, False])
        self.assertEqual(declared["declared_by"].tolist(), [["al"], []])
        self.assertEqual(declared["resource_identification"].tolist(), ["address_only", "address_only"])  # what the data identifies does not change
        unverified = classify(data, cfg("addrlevel_unverified"), REGISTER, None, LADOK)
        self.assertEqual(unverified["declared_address_level"].tolist(), [False, False])  # a hypothesis classifies nothing

    def test_s_c_mixed_and_defective_extract_each_row_in_its_place(self) -> None:
        data = rows(row("1", "Gata 1", "Sal 1"), row("2", "Gata 2", ""), row("3", "Gata 1", "Sal 9"), row("4", "", ""), row("5", "Gata 1", "Sal 2", places="0"),
                    row("6", "Gata 1", "Sal 1", places="150"), row("7", "Hemma", "Hemtenta"), row("8", "Gata 1", "Sal 1", time="-", date=""))
        result = classify(data, cfg("nonphys_unverified"), REGISTER, None, LADOK)
        self.assertEqual(result["resource_identification"].tolist(), ["room_matched", "address_only", "room_named_not_in_register", "no_address", "room_matched",
                                                                      "room_matched", "room_named_not_in_register", "room_matched"])  # row 7: Hemma/Hemtenta is a candidate only, here not in the register
        flags = result["flags"].tolist()
        self.assertIn("room_not_in_register", flags[2])
        self.assertIn("capacity_missing_in_register", flags[4])
        self.assertIn("places_missing_or_zero", flags[4])
        self.assertIn("places_exceed_capacity", flags[5])
        self.assertEqual(sorted(flags[7]), ["date_missing", "time_unparseable"])
        self.assertEqual(result["candidate_rule_ids"][6], ["np"])  # a candidate is noted for the row
        self.assertEqual(result["capacity"][5], 100)

    def test_verified_rules_change_the_classification_without_code(self) -> None:
        data = rows(row("1", "Hemma", "Hemtenta"), row("2", "Sal utan anpassningar", ""))
        before = classify(data, cfg("nonphys_unverified"), REGISTER, None, LADOK)
        after = classify(data, cfg("nonphys_verified", "notaddr_verified"), REGISTER, None, LADOK)
        self.assertNotIn("declared_non_physical", set(before["resource_identification"]))
        self.assertEqual(after["resource_identification"].tolist(), ["declared_non_physical", "no_address"])
        self.assertIn("address_field_not_an_address", after["flags"][1])

    def test_status_classes_never_guess_unlisted_statuses(self) -> None:
        result = classify(rows(row("1", "Gata 1", "Sal 1", status="Avbokad", date="", time="-", places="0"), row("2", "Gata 1", "Sal 1", status="Under behandling")),
                          cfg(), REGISTER, None, LADOK)
        self.assertEqual(result["status_class"].tolist(), ["cancelled", "unclassified"])
        self.assertEqual(result["flags"][0], [])  # findings about date, time and places are raised only for rows that are not cancelled
        self.assertEqual(result["flags"][1], ["status_unclassified"])

    def test_the_dimensions_are_independent(self) -> None:
        """A booking can be address-only, outside Ladok coverage, with an ambiguous link and an unclassified status at the same time."""
        link = pd.DataFrame([("p1", "a1", "ambiguous_candidates"), ("p1", "a2", "ambiguous_candidates")], columns=["placement_id", "activity_id", "candidate_status"])
        result = classify(rows(row("p1", "Gata 2", "", status="Under behandling", date="2026-06-01")), cfg(), REGISTER, link, LADOK)
        self.assertEqual((result["resource_identification"][0], result["ladok_coverage"][0], result["link_certainty"][0], result["status_class"][0]),
                         ("address_only", "outside", "ambiguous", "unclassified"))


class CoverageAndLinkTests(unittest.TestCase):
    def test_s_e_coverage_is_derived_and_told_apart_from_link_quality(self) -> None:
        link = pd.DataFrame([("a", "act1", "single_candidate")], columns=["placement_id", "activity_id", "candidate_status"])
        data = rows(row("a", "Gata 1", "Sal 1", date="2026-02-09"), row("b", "Gata 1", "Sal 1", date="2026-02-10"), row("c", "Gata 1", "Sal 1", date="2026-06-01"),
                    row("d", "Gata 1", "Sal 1", date=""))
        result = classify(data, cfg(), REGISTER, link, LADOK)
        self.assertEqual(result["ladok_coverage"].tolist(), ["within", "within", "outside", "unknown"])
        self.assertEqual(result["link_certainty"].tolist(), ["unique", "none_within_coverage", "none_outside_coverage", "none_coverage_unknown"])

    def test_window_is_derived_overridden_or_unknown(self) -> None:
        config = cfg()
        self.assertEqual(ladok_window(config, LADOK), {"first": "2026-01-12", "last": "2026-03-31", "origin": "derived"})
        self.assertEqual(ladok_window(config, None)["origin"], "unknown")
        folder = Path(tempfile.mkdtemp())
        (folder / "q.toml").write_text(BASE_CONFIG.replace('date_column = "start_date"', 'date_column = "start_date"\noverride_first = "2026-02-01"\noverride_last = "2026-02-28"'), encoding="utf-8")
        self.assertEqual(ladok_window(load_config(folder / "q.toml"), LADOK), {"first": "2026-02-01", "last": "2026-02-28", "origin": "override"})
        self.assertEqual(classify(rows(row("1", "Gata 1", "Sal 1")), cfg(), REGISTER, None, None)["ladok_coverage"][0], "unknown")  # no Ladok data: coverage unknown

    def test_link_rule_does_not_depend_on_row_order_and_counts_distinct_activities(self) -> None:
        one = pd.DataFrame([("p", "a1", "single_candidate"), ("p", "a1", "single_candidate")], columns=["placement_id", "activity_id", "candidate_status"])
        two = pd.DataFrame([("p", "a1", "single_candidate"), ("p", "a2", "single_candidate")], columns=["placement_id", "activity_id", "candidate_status"])
        mixed = pd.DataFrame([("p", "", "no_candidate"), ("p", "a1", "single_candidate")], columns=["placement_id", "activity_id", "candidate_status"])
        data = rows(row("p", "Gata 1", "Sal 1"))
        self.assertEqual(classify(data, cfg(), REGISTER, one, LADOK)["link_certainty"][0], "unique")
        self.assertEqual(classify(data, cfg(), REGISTER, two, LADOK)["link_certainty"][0], "ambiguous")
        self.assertEqual(classify(data, cfg(), REGISTER, mixed, LADOK)["link_certainty"][0], "unique")
        self.assertEqual(classify(data, cfg(), REGISTER, mixed.iloc[::-1].reset_index(drop=True), LADOK)["link_certainty"][0], "unique")
        self.assertEqual(classify(data, cfg(), REGISTER, None, LADOK)["link_certainty"][0], "not_assessed")


class ConfigTests(unittest.TestCase):
    def _load(self, text: str):
        path = Path(tempfile.mkdtemp()) / "q.toml"
        path.write_text(text, encoding="utf-8")
        return load_config(path)

    def test_the_bundled_configuration_is_valid_and_only_confirmed_rules_are_verified(self) -> None:
        config = load_config()
        self.assertEqual({r.id for r in config.rules if r.verified}, {"status-avbokad", "status-klar", "candidate-hemma", "candidate-hemtenta"})  # home exams: confirmed by the user 2026-10-13
        self.assertEqual(config.rules_of("address_level"), ())  # absence of a room name is not a declaration
        self.assertEqual(len(config.digest), 64)
        under_review = {r.value_class for r in config.rules_of("status")}
        self.assertEqual(under_review, {"cancelled", "active"})  # "Under behandling" and "Andring begard" have no rule

    def test_a_verified_rule_needs_a_source_and_every_rule_needs_a_field_and_a_unique_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "verifierad men anger ingen källa"):
            self._load(BASE_CONFIG + '[[non_physical_rule]]\nid = "x"\naddress = "A"\nverified = true\n')
        with self.assertRaisesRegex(ValueError, "inget fält att matcha"):
            self._load(BASE_CONFIG + '[[non_physical_rule]]\nid = "x"\nverified = false\n')
        with self.assertRaisesRegex(ValueError, "måste vara unika"):
            self._load(BASE_CONFIG + '[[non_physical_rule]]\nid = "st-active"\naddress = "A"\nverified = false\n')
        with self.assertRaisesRegex(ValueError, "verified måste vara"):
            self._load(BASE_CONFIG + '[[non_physical_rule]]\nid = "x"\naddress = "A"\n')
        with self.assertRaisesRegex(ValueError, "okänd statusklass"):
            self._load(BASE_CONFIG.replace('class = "active"', 'class = "waiting"'))
        with self.assertRaisesRegex(ValueError, "okända fält"):
            self._load(BASE_CONFIG + '[[non_physical_rule]]\nid = "x"\naddress = "A"\nverified = false\ncolour = "red"\n')
        with self.assertRaisesRegex(ValueError, "schemat"):
            self._load(BASE_CONFIG.replace("booking-data-quality-v1", "v0"))

    def test_other_column_names_in_a_new_extract_need_only_configuration(self) -> None:
        renamed = BASE_CONFIG + '\n[columns]\naddress = "adress"\nroom = "sal"\nstatus = "tillstand"\n'
        config = self._load(renamed)
        data = rows(row("1", "Gata 1", "Sal 1")).rename(columns={"address": "adress", "room": "sal", "status": "tillstand"})
        self.assertEqual(classify(data, config, REGISTER, None, LADOK)["resource_identification"][0], "room_matched")


class AssessTests(unittest.TestCase):
    def test_the_report_counts_each_dimension_and_names_unclassified_statuses_and_candidates(self) -> None:
        folder = Path(tempfile.mkdtemp())
        data = rows(row("1", "Gata 1", "Sal 1"), row("2", "Gata 2", ""), row("3", "Gata 2", "", status="Under behandling"), row("4", "", "", status="Avbokad", date="", time="-", places="0"),
                    row("5", "Hemma", "Hemtenta"))
        data.to_csv(folder / "bookings.csv", index=False, encoding="utf-8-sig")
        REGISTER.to_csv(folder / "room_inventory.csv", index=False, encoding="utf-8-sig")
        LADOK.to_csv(folder / "ladok_activities.csv", index=False, encoding="utf-8-sig")
        path = folder / "q.toml"
        path.write_text(BASE_CONFIG + EXTRA["nonphys_unverified"], encoding="utf-8")
        report = assess(folder, path)
        self.assertEqual((report["rows"], report["rows_not_cancelled"]), (5, 4))
        self.assertEqual(report["missing_sources"], ["linkage"])  # named, not guessed
        self.assertEqual(report["resource_identification"]["address_only"], 2)
        self.assertEqual(report["resource_identification_by_address"]["Gata 2"]["address_only"], 2)
        self.assertEqual(report["unclassified_statuses"], {"Under behandling": 1})
        self.assertEqual(report["candidate_rule_matches"], {"np": 1})
        self.assertEqual(report["declared_address_level_rows"], 0)
        self.assertEqual(report["link_certainty"]["not_assessed"], 4)
        self.assertEqual(report["config"]["unverified_rules"], ["np"])
        self.assertEqual(report["source_coverage"]["ladok"]["origin"], "derived")
        with self.assertRaises(FileNotFoundError):
            assess(Path(tempfile.mkdtemp()), path)


@unittest.skipUnless((Path(__file__).resolve().parents[1] / "data" / "processed" / "bookings.csv").is_file(), "kräver lokalt genererat underlag (data/processed)")
class RealDataTests(unittest.TestCase):
    def test_counts_agree_with_an_independent_count(self) -> None:
        processed = Path(__file__).resolve().parents[1] / "data" / "processed"
        raw = pd.read_csv(processed / "bookings.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
        report = assess(processed)
        live = raw[raw["status"] != "Avbokad"]
        self.assertEqual(report["rows_not_cancelled"], len(live))
        home = (live["address"] == "Hemma") | (live["room"] == "Hemtenta")  # confirmed non-physical: declared_non_physical, not address_only
        self.assertEqual(report["resource_identification"]["address_only"], int(((live["room"] == "") & (live["address"] != "") & ~home).sum()))
        self.assertEqual(report["resource_identification"]["declared_non_physical"], int(home.sum()))
        self.assertEqual(sum(report["resource_identification"].values()), len(live))
        self.assertEqual(sum(report["link_certainty"].values()), len(live))
        self.assertEqual(report["declared_address_level_rows"], 0)


if __name__ == "__main__":
    unittest.main()
