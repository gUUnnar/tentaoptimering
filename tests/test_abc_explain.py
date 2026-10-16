"""The saving between two alternatives, explained: hand-worked cases for each way the total can change.

Rooms: `own-a` (rent 100 000, 100 seats), `own-b` (rent 40 000), `far` (rent 10 000, 90 minutes of paid travel),
`ext-1` (external, 30 000 per session, 30 minutes of travel). Staff: ladder 100 -> 1, 200 -> 2, preparation and closing 30,
10 öre per paid minute, shortest paid pass 120. An exam of 120 minutes is one pass of 30 + 120 + 30 = 180 paid minutes.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tentaoptimering.abc_explain import explain  # noqa: E402
from tentaoptimering.abc_ledger import COST_KIND_ACTUAL, COST_KIND_RUN, Ledger, actual_ledger  # noqa: E402
from tentaoptimering.cost_realization import classify_room, summarize  # noqa: E402
from tentaoptimering.joint_contract import (  # noqa: E402
    INPUT_SCHEMA_VERSION, CandidateSlot, ExamDemand, JointOptimizationInput, ParticipantGroup, Room, ScopeSummary, SolverSettings,
    StaffingCostPolicy, StaffingStep,
)
from tentaoptimering.joint_pricing import PricedSession, price, staffing_totals  # noqa: E402

DAY = date(2026, 1, 12)
SLOTS = (CandidateSlot("am", DAY, "08:00", 480, 1200), CandidateSlot("pm", DAY, "14:00", 840, 1200))


def _problem(rate: int = 10, own_a_rent: int = 100_000, resource_basis=None, extra_rooms=()) -> JointOptimizationInput:
    rooms = (
        Room("own-a", "b1", "Uppsala", 100, own_a_rent, name="Egen sal A", cost_object_id="ko-a", cost_origin="simulated"),
        Room("own-b", "b1", "Uppsala", 100, 40_000, name="Egen sal B", cost_object_id="ko-a", cost_origin="simulated"),
        Room("far", "b2", "Uppsala", 100, 10_000, name="Fjärran sal", travel_paid_minutes=90, cost_origin="simulated"),
        Room("ext-1", "b3", "Uppsala", 100, 0, 30_000, name="Extern hall", kind="external", travel_paid_minutes=30, cost_origin="simulated"),
    ) + tuple(extra_rooms)
    demands = tuple(ExamDemand(f"exam-{name}", (ParticipantGroup(f"{name}-g", count, (f"{name}-a",), "registered_count"),), 120, "Uppsala", ("am", "pm"), "am")
                    for name, count in (("e1", 60), ("e2", 60), ("e3", 40)))
    return JointOptimizationInput(INPUT_SCHEMA_VERSION, "explain", "hash", SLOTS, demands, rooms, StaffingCostPolicy((StaffingStep(100, 1), StaffingStep(200, 2)), 0, 0, 30, 30, rate, 120),
                                  SolverSettings(5, 1, 1), (), ScopeSummary(3, 3, 0, 0, 3, 160), 30, resource_basis=resource_basis)


def _session(room: str, start: int, participants: int, *exams: str) -> PricedSession:
    return PricedSession(room, DAY, start, start + 120, participants, 1 if participants <= 100 else 2, tuple(exams))


def _ledger(ref: str, name: str, problem: JointOptimizationInput, sessions: list[PricedSession], kind: str = "C", snapshot=None) -> Ledger:
    exams = {}
    for session in sessions:
        for exam in session.exam_ids:
            row = exams.setdefault(exam, {"exam_event_id": exam, "course": exam.upper(), "participants": 0, "date": DAY.isoformat(), "start": f"{session.start_minute // 60:02d}:00",
                                          "end": None, "rooms": [], "labels": [], "requires_room": True})
            row["rooms"].append(session.room_id)
            row["labels"].append(session.room_id)
    components = price(problem, sessions)
    return Ledger(ref, kind, name, problem, snapshot, COST_KIND_RUN, sessions, exams, components, staffing_totals(problem, sessions), "hash", 160)


LEFT_SESSIONS = [_session("own-a", 480, 60, "e1"), _session("ext-1", 480, 60, "e2"), _session("own-b", 840, 40, "e3")]
RIGHT_SESSIONS = [_session("own-a", 480, 60, "e1"), _session("own-a", 840, 100, "e2", "e3")]


class ExplainedSavingTests(unittest.TestCase):
    def test_the_three_cost_items_sum_to_the_total_difference_and_name_the_rooms_and_bookings(self) -> None:
        left, right = _ledger("l", "Före", _problem(), LEFT_SESSIONS), _ledger("r", "Efter", _problem(), RIGHT_SESSIONS)
        # left 100 000 + 40 000 rent, 30 000 external, 180 + 210 + 180 = 570 paid minutes = 5 700; right 100 000 rent, 360 minutes = 3 600
        self.assertEqual((left.total, right.total), (175_700, 103_600))
        result = explain(left, right)
        self.assertTrue(result["available"])
        self.assertEqual(result["total"]["difference_ore"], -72_100)
        items = {item["key"]: item for item in result["items"]}
        self.assertEqual((items["rooms"]["difference_ore"], items["external"]["difference_ore"], items["staff"]["difference_ore"]), (-40_000, -30_000, -2_100))
        self.assertEqual(sum(item["difference_ore"] for item in result["items"]), result["total"]["difference_ore"])
        # named rooms: own-b can be released, the external hall is no longer used
        rooms = {row["room_id"]: row for row in result["rooms"]}
        self.assertEqual((rooms["own-b"]["status"], rooms["own-b"]["fixed_difference_ore"], rooms["own-b"]["name"]), ("avoidable", -40_000, "Egen sal B"))
        self.assertEqual((rooms["ext-1"]["status"], rooms["ext-1"]["external_difference_ore"]), ("avoidable", -30_000))
        self.assertEqual(rooms["own-a"]["status"], "kept")
        self.assertEqual(sum(row["fixed_difference_ore"] for row in result["rooms"]), items["rooms"]["difference_ore"])
        self.assertEqual(sum(row["external_difference_ore"] for row in result["rooms"]), items["external"]["difference_ore"])
        # an external booking is avoided
        external = result["sessions"]["external"]
        self.assertEqual((len(external["avoided"]), external["avoided_ore"], external["avoided"][0]["exams"]), (1, 30_000, ["e2"]))
        # fewer passes and fewer paid hours: 3 -> 2 passes, 570 -> 360 minutes
        staffing = result["staffing"]
        self.assertEqual((staffing["left"]["passes"], staffing["right"]["passes"], staffing["difference"]["paid_minutes"]), (3, 2, -210))
        # the changed exams carry what explains them
        changed = {row["exam_event_id"]: row for row in result["exams"]["changed"]}
        self.assertEqual(set(changed), {"e2", "e3"})
        self.assertIn("external_avoided", changed["e2"]["tags"])
        self.assertIn("room_freed:own-b", changed["e3"]["tags"])
        self.assertTrue(all(item["drivers"] for item in result["items"]))

    def test_more_paid_hours_can_lower_the_total_cost(self) -> None:
        left = _ledger("l", "Dyr sal", _problem(), [_session("own-a", 480, 60, "e1")])
        right = _ledger("r", "Billig sal med restid", _problem(), [_session("far", 480, 60, "e1")])
        result = explain(left, right)
        # own-a: rent 100 000 + 180 minutes; far: rent 10 000 + 270 minutes (90 travel): +900 for staff, -90 000 for rent
        self.assertEqual(result["staffing"]["difference"]["paid_minutes"], 90)
        self.assertEqual({item["key"]: item["difference_ore"] for item in result["items"]}, {"rooms": -90_000, "external": 0, "staff": 900})
        self.assertEqual(result["total"]["difference_ore"], -89_100)
        self.assertTrue(result["staffing"]["difference"]["paid_minutes"] > 0 > result["total"]["difference_ore"])

    def test_fewer_paid_hours_lower_the_staff_cost(self) -> None:
        left = _ledger("l", "Två pass", _problem(), [_session("own-a", 480, 60, "e1"), _session("own-b", 480, 60, "e2")])
        right = _ledger("r", "Ett pass", _problem(), [_session("own-a", 480, 100, "e1", "e2")])
        result = explain(left, right)
        items = {item["key"]: item for item in result["items"]}
        self.assertEqual((items["staff"]["difference_ore"], items["rooms"]["difference_ore"]), (-1_800, -40_000))
        self.assertEqual(result["staffing"]["difference"]["passes"], -1)

    def test_a_room_that_is_no_longer_used_without_a_verified_rent_saving_is_conditional(self) -> None:
        snapshot = {"pack_id": "p", "origin": "simulated", "sha256": "x",
                    "rooms": [{"room_id": "own-a", "cost_object_id": "ko-a"}, {"room_id": "own-b", "cost_object_id": "ko-a"}],
                    "cost_objects": [{"cost_object_id": "ko-a", "name": "Avtal A", "kind": "internal_rent", "annual_cost_ore": 140_000, "avoidable": "yes", "notice_months": 6,
                                      "earliest_release_date": "2027-07-01", "one_off_cost_ore": 0, "provenance": {"origin": "simulated"}}]}
        left, right = _ledger("l", "Före", _problem(), LEFT_SESSIONS), _ledger("r", "Efter", _problem(), RIGHT_SESSIONS, snapshot=snapshot)
        result = explain(left, right)
        by_room = {item["room_id"]: item["realization"] for item in result["realization"]["items"]}
        # own-b is avoidable by the terms but shares the contract with own-a, which is still used
        self.assertEqual(by_room["own-b"]["status"], "blocked_shared")
        self.assertEqual(result["realization"]["summary"]["verified_ore"], 0)
        self.assertFalse(result["savings_kinds"]["verified_realisable"]["available"])
        self.assertFalse(result["savings_kinds"]["theoretical_annual_potential"]["available"])
        self.assertFalse(result["savings_kinds"]["historical"]["available"])
        self.assertTrue(result["data_quality"]["simulated"])

    def test_without_contract_data_the_saving_is_conditional_and_never_verified(self) -> None:
        self.assertEqual(classify_room(None, "own-b", "internal", set())["status"], "conditional")
        free = {"rooms": [{"room_id": "r", "cost_object_id": "k"}], "cost_objects": [{"cost_object_id": "k", "name": "K", "kind": "internal_rent", "annual_cost_ore": 5, "avoidable": "yes",
                                                                                      "notice_months": 6, "earliest_release_date": "2027-01-01", "one_off_cost_ore": 0,
                                                                                      "provenance": {"origin": "observed"}}]}
        self.assertEqual(classify_room(free, "r", "internal", set())["status"], "verified")  # observed terms, no shared room in use
        for origin in ("simulated", "assumption", "model_calculated"):
            unproven = {**free, "cost_objects": [{**free["cost_objects"][0], "provenance": {"origin": origin}}]}
            self.assertEqual(classify_room(unproven, "r", "internal", set())["status"], "possible_unverified", origin)
        blocked = {**free, "cost_objects": [{**free["cost_objects"][0], "avoidable": "no"}]}
        self.assertEqual(classify_room(blocked, "r", "internal", set())["status"], "blocked_contract")
        items = [{"modelled_saving_ore": 100, "realization": {"status": "verified"}}, {"modelled_saving_ore": 50, "realization": {"status": "conditional"}},
                 {"modelled_saving_ore": 25, "realization": {"status": "blocked_contract"}}]
        self.assertEqual({key: value for key, value in summarize(items).items() if key.endswith("_ore")},
                         {"modelled_saving_ore": 175, "verified_ore": 100, "conditional_ore": 50, "blocked_ore": 25})

    def test_changed_prices_are_split_from_changed_use_of_rooms(self) -> None:
        left = _ledger("l", "Före", _problem(own_a_rent=100_000), [_session("own-a", 480, 60, "e1"), _session("own-b", 480, 60, "e2")])
        right = _ledger("r", "Efter", _problem(own_a_rent=150_000), [_session("own-a", 480, 100, "e1", "e2")])
        result = explain(left, right)
        # right 150 000 rent + 180 minutes (1 800) = 151 800; left 100 000 + 40 000 + 3 600 = 143 600
        self.assertEqual(result["total"]["difference_ore"], 8_200)
        # the right plan at the left prices: 100 000 + 1 800 = 101 800, so using fewer rooms saves 41 800 and the dearer rent adds 50 000
        self.assertEqual((result["split"]["usage_ore"], result["split"]["assumption_ore"]), (-41_800, 50_000))
        self.assertEqual(result["split"]["usage_ore"] + result["split"]["assumption_ore"], result["total"]["difference_ore"])
        rooms_item = next(item for item in result["items"] if item["key"] == "rooms")
        self.assertEqual((rooms_item["usage_ore"], rooms_item["assumption_ore"]), (-40_000, 50_000))

    def test_misleading_comparisons_are_blocked_with_the_reason(self) -> None:
        left = _ledger("l", "Före", _problem(), LEFT_SESSIONS)
        fewer = _ledger("r", "Färre tentor", _problem(), [_session("own-a", 480, 60, "e1")])
        result = explain(left, fewer)
        self.assertFalse(result["available"])
        self.assertIsNone(result["total"]["difference_ore"])
        self.assertTrue(any("olika tentamina" in text for text in result["reasons"]))
        # a blocked comparison reports no difference at all, neither in total nor per cost item nor as a split
        self.assertTrue(all(item["difference_ore"] is None and item["usage_ore"] is None and item["drivers"] == [] for item in result["items"]))
        self.assertFalse(result["split"]["available"])
        self.assertIsNone(result["summary"])
        other = _ledger("r", "Annat underlag", _problem(), RIGHT_SESSIONS)
        other.dataset_hash = "other"
        self.assertTrue(any("olika dataunderlag" in text for text in explain(left, other)["reasons"]))
        demand = _ledger("r", "Mer efterfrågan", _problem(), RIGHT_SESSIONS)
        demand.participants = 200
        self.assertTrue(any("Efterfrågan skiljer" in text for text in explain(left, demand)["reasons"]))


def _actual_profile(places_by_exam: dict[str, list[dict]], statuses: dict[str, str] | None = None) -> dict:
    exams = []
    for exam_id, places in places_by_exam.items():
        start, end = ("14:00", "16:00") if exam_id == "e3" else ("08:00", "10:00")  # e3 is the afternoon exam
        exams.append({"exam_event_id": exam_id, "course": exam_id.upper(), "participants": {"e1": 60, "e2": 60, "e3": 40}[exam_id], "status": (statuses or {}).get(exam_id, "booked"), "date": DAY.isoformat(), "start": start,
                      "end": end, "places": places, "not_booked_reason": "Avbokad"})
    return {"ref": "actual", "kind": "A", "name": "A – Faktisk bokning", "exams": exams}


def _place(room_id: str | None, places: int, identification: str = "room_matched", label: str | None = None) -> dict:
    return {"label": label or room_id or "Adress", "room_id": room_id, "booked_places": places, "identification": identification}


class ActualBookingPricingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = _ledger("run", "Körning", _problem(), [_session("own-a", 480, 60, "e1"), _session("own-b", 480, 60, "e2"), _session("own-a", 840, 40, "e3")])

    def test_the_actual_booking_is_priced_by_the_runs_rules_and_labelled_as_model_calculated(self) -> None:
        profile = _actual_profile({"e1": [_place("own-a", 60)], "e2": [_place("ext-1", 60)], "e3": [_place("own-a", 40)]})
        actual = actual_ledger(profile, self.rules)
        self.assertEqual(actual.cost_kind, COST_KIND_ACTUAL)
        self.assertTrue(actual.complete)
        # own-a rent 100 000; ext-1 one session 30 000; three passes 180 + 210 + 180 = 570 minutes = 5 700
        self.assertEqual(actual.total, 135_700)
        self.assertEqual(actual.staffing["passes"], 3)
        result = explain(actual, self.rules)
        self.assertTrue(result["available"])
        self.assertEqual(result["basis"]["left"]["cost_kind"], COST_KIND_ACTUAL)
        self.assertEqual(result["basis"]["left"]["staffing_origin"], "model_calculated_from_booked_places")
        self.assertIn("inte faktisk kostnad", result["basis"]["left"]["cost_kind_text"])
        self.assertEqual(result["total"]["difference_ore"], self.rules.total - 135_700)

    def test_a_booking_with_only_an_address_is_accepted_under_the_temporary_rule(self) -> None:
        profile = _actual_profile({"e1": [_place("own-a", 60)], "e2": [{**_place(None, 60, "address_only", "Gata 1 (sal saknas i uttaget)"), "address": "Gata 1"}], "e3": [_place("own-a", 40)]})
        actual = actual_ledger(profile, self.rules)
        self.assertTrue(actual.complete)
        self.assertEqual(profile["exams"][1]["places"][0]["room_id"], None)  # the cached profile of A is not changed
        # rent of the unknown room counts as zero; its staff follow from the booked places: rent 100 000 + three passes of 180 minutes
        self.assertEqual(actual.total, 100_000 + 3 * 180 * 10)
        self.assertTrue(actual.assumptions)
        result = explain(actual, self.rules)
        self.assertTrue(result["available"], result["reasons"])
        self.assertTrue(any(flag["key"] == "address_only_assumed" for flag in result["data_quality"]["flags"]))

    def test_a_booking_in_a_room_the_run_lacks_blocks_the_total_and_is_listed(self) -> None:
        profile = _actual_profile({"e1": [_place("own-a", 60)], "e2": [_place("okand-sal", 60)], "e3": [_place("own-a", 40)]})
        actual = actual_ledger(profile, self.rules)
        self.assertFalse(actual.complete)
        self.assertEqual([item["exam_event_id"] for item in actual.unpriced], ["e2"])
        result = explain(actual, self.rules)
        self.assertFalse(result["available"])
        self.assertIsNone(result["total"]["difference_ore"])
        self.assertTrue(any("kan inte prissättas fullständigt" in text for text in result["reasons"]))

    def test_an_exam_that_was_not_booked_blocks_the_comparison(self) -> None:
        profile = _actual_profile({"e1": [_place("own-a", 60)], "e2": [], "e3": [_place("own-a", 40)]}, {"e2": "not_booked"})
        self.assertFalse(actual_ledger(profile, self.rules).complete)

    def test_observed_staffing_is_kept_apart_and_labelled_with_its_origin(self) -> None:
        snapshot = {"actual_staffing": [{"date": DAY.isoformat(), "room_id": "own-a", "staff_count": 3, "paid_minutes": 500, "provenance": {"origin": "simulated"}},
                                        {"date": "2026-02-02", "room_id": "own-a", "staff_count": 1, "paid_minutes": 100, "provenance": {"origin": "observed"}}]}
        rules = replace(self.rules, snapshot=snapshot)
        actual = actual_ledger(_actual_profile({"e1": [_place("own-a", 60)], "e2": [_place("own-b", 60)], "e3": [_place("own-a", 40)]}), rules)
        self.assertEqual([(row["room_id"], row["origin"]) for row in actual.observed_staffing], [("own-a", "simulated")])
        self.assertEqual(actual.staffing["passes"], 3)  # the modelled staffing is untouched by the recorded rows


if __name__ == "__main__":
    unittest.main()
