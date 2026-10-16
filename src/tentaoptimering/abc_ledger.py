"""A cost ledger per alternative: the placement as priced sessions, its cost components and what the figures rest on.

`run_ledger` reads a saved run (B or C) from its own artifacts. `actual_ledger` prices the actual booking (A) by the rules of
a run, so that A and the run are costed by one rule set. A's cost is then *model calculated for the historical bookings*; it
is never called historical cost, and its staffing is never called observed. Where a booking cannot be priced (it names only
an address, or a room that the run does not have) the ledger says so and is not complete: nothing is guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from typing import Any

from .joint_contract import JointOptimizationInput, Room, read_problem
from .joint_options import building_id
from .joint_pricing import COMPONENTS, PricedSession, price, staffing_totals

SNAPSHOT_FILE = "resource_pack.json"
COST_KIND_RUN = "model_calculated"
COST_KIND_ACTUAL = "model_calculated_for_historical_bookings"
NON_ROOM = "declared_non_physical"
ADDRESS_ONLY = "address_only"
# TEMPORARY RULE: a booking that names only an address is accepted on the assumption that the address has a room with more places than
# the number registered for the exam. Its rent is unknown and counts as zero; its staff follow from the booked places. Remove when the
# bookings identify their rooms.
ADDRESS_ONLY_RULE = True


@dataclass
class Ledger:
    ref: str
    kind: str
    name: str
    problem: JointOptimizationInput
    snapshot: dict[str, Any] | None
    cost_kind: str
    sessions: list[PricedSession]
    exams: dict[str, dict[str, Any]]
    components: dict[str, int]
    staffing: dict[str, Any]
    dataset_hash: str | None = None
    participants: int = 0
    complete: bool = True
    unpriced: list[dict[str, Any]] = field(default_factory=list)
    gap_ore: int | None = None
    proven_optimum: bool | None = None
    observed_staffing: list[dict[str, Any]] = field(default_factory=list)
    # Temporary rules that were applied to price the booking (for example address-only bookings), shown with the result.
    assumptions: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.components["comparable_total_cost_ore"]

    @property
    def exam_ids(self) -> frozenset[str]:
        return frozenset(self.exams)


def read_snapshot(directory: Path) -> dict[str, Any] | None:
    path = Path(directory) / SNAPSHOT_FILE
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _exam_row(exam: dict[str, Any]) -> dict[str, Any]:
    return {"exam_event_id": exam["exam_event_id"], "course": exam.get("course"), "participants": exam.get("participants"), "date": exam.get("date"), "start": exam.get("start"),
            "end": exam.get("end"), "rooms": [p["room_id"] for p in exam.get("places", ()) if p.get("room_id")],
            "labels": [p["label"] for p in exam.get("places", ())], "requires_room": exam.get("requires_room", True)}


def run_ledger(directory: Path, profile: dict[str, Any]) -> Ledger:
    """The ledger of a saved run with a verified solution; `profile` is its `run_profile` (placement in the shared exam form)."""
    problem = read_problem(Path(directory) / "joint_input.json")
    result = json.loads((Path(directory) / "joint_result.json").read_text(encoding="utf-8"))
    from .joint_pricing import sessions_from_result

    sessions = [replace(item, exam_ids=tuple(name.removeprefix("exam-") for name in item.exam_ids)) for item in sessions_from_result(problem, result)]  # event ids, as in A
    reported = result.get("costs") or {}
    components = {name: int(reported.get(name, 0)) for name in (*COMPONENTS, "comparable_total_cost_ore")}
    exams = {item["exam_event_id"]: _exam_row(item) for item in profile.get("exams", ()) if item.get("status") == "placed"}
    cost = profile.get("cost") or {}
    return Ledger(profile["ref"], profile["kind"], profile["name"], problem, read_snapshot(directory), COST_KIND_RUN, sessions, exams, components,
                  staffing_totals(problem, sessions), problem.dataset_hash, sum(item.participant_count for item in problem.demands), True, [],
                  cost.get("gap_ore"), cost.get("proven_optimum"))


def _minutes(text: str | None) -> int | None:
    return None if not text else int(text[:2]) * 60 + int(text[3:5])


def actual_ledger(profile: dict[str, Any], rules: Ledger) -> Ledger:
    """A (the actual booking) priced by the rules of `rules` (a run's ledger). Bookings that cannot be priced are listed, not guessed."""
    problem = rules.problem
    rooms = {room.room_id for room in problem.rooms}
    assumed: dict[str, int] = {}  # address room id -> bookings accepted under the temporary address rule
    sessions: dict[tuple[str, str, int], dict[str, Any]] = {}
    exams: dict[str, dict[str, Any]] = {}
    unpriced: list[dict[str, Any]] = []
    for exam in profile.get("exams", ()):
        if exam.get("exam_event_id") not in rules.exams:
            continue  # A is read for the run's exams only; this guards a profile with a wider scope
        places = [dict(item) for item in exam.get("places", ())]  # a copy: the cached profile of A is never changed
        row = _exam_row({**exam, "places": places})
        exams[exam["exam_event_id"]] = row
        if exam["status"] != "booked":
            unpriced.append({"exam_event_id": exam["exam_event_id"], "course": exam.get("course"), "reason": exam.get("not_booked_reason") or "Tentamen saknar bokning."})
            continue
        start, end = _minutes(exam["start"]), _minutes(exam["end"])
        if ADDRESS_ONLY_RULE:
            for place in places:
                if place["identification"] == ADDRESS_ONLY and place.get("address") and not place.get("room_id"):
                    place["room_id"] = f"adress:{building_id(place['address'])}"
                    assumed[place["room_id"]] = assumed.get(place["room_id"], 0) + 1
                    rooms.add(place["room_id"])
        row["rooms"] = [p["room_id"] for p in places if p.get("room_id")]
        bad = [p for p in places if p["identification"] != NON_ROOM and (not p.get("room_id") or p["room_id"] not in rooms)]
        if start is None or end is None:
            unpriced.append({"exam_event_id": exam["exam_event_id"], "course": exam.get("course"), "reason": "Bokningen saknar tolkbart klockslag."})
            continue
        for place in bad:
            why = "bara adress angiven" if place["identification"] == "address_only" else "sal saknas i körningens lokalbestånd och har därför inget pris"
            unpriced.append({"exam_event_id": exam["exam_event_id"], "course": exam.get("course"), "reason": f"{place['label']}: {why}."})
        for place in places:
            if place.get("room_id") not in rooms:
                continue
            key = (place["room_id"], exam["date"], start)
            session = sessions.setdefault(key, {"participants": 0, "end": end if end > start else end + 1440, "exams": []})
            session["participants"] += int(place["booked_places"])
            session["end"] = max(session["end"], end if end > start else end + 1440)
            session["exams"].append(exam["exam_event_id"])
    from .joint_pricing import reprice_staff
    from datetime import date as _date

    if assumed:
        extra = tuple(Room(room_id, room_id.removeprefix("adress:"), "address", 1, 0, name=f"Adress {room_id.removeprefix('adress:')} (sal antagen)", cost_origin="assumption")
                      for room_id in sorted(assumed))
        problem = replace(problem, rooms=problem.rooms + extra)

    priced = reprice_staff(problem, [PricedSession(room, _date.fromisoformat(day), start, value["end"], value["participants"], 0, tuple(sorted(set(value["exams"]))))
                                     for (room, day, start), value in sorted(sessions.items())])
    totals = price(problem, priced)
    observed = _observed_staffing(rules.snapshot, priced)
    return Ledger(profile["ref"], profile["kind"], profile["name"], problem, rules.snapshot, COST_KIND_ACTUAL, priced, exams, totals, staffing_totals(problem, priced),
                  rules.dataset_hash, sum(item.get("participants") or 0 for item in exams.values()), not unpriced, unpriced, None, None, observed,
                  [f"{count} bokningar med bara adress ({room_id.removeprefix('adress:')}) är godtagna enligt den temporära regeln att adressen har en sal med fler platser än antalet anmälda; hyran är okänd och räknas som noll, bemanningen följer bokade platser." for room_id, count in sorted(assumed.items())])


def _observed_staffing(snapshot: dict[str, Any] | None, sessions: list[PricedSession]) -> list[dict[str, Any]]:
    """Recorded staffing of the pack for the rooms and dates of the booking, with its origin. Never merged into the modelled staffing."""
    if not snapshot:
        return []
    keys = {(s.room_id, s.day.isoformat()) for s in sessions}
    return [{"date": row["date"], "room_id": row["room_id"], "staff_count": row["staff_count"], "paid_minutes": row["paid_minutes"], "origin": row["provenance"]["origin"]}
            for row in snapshot.get("actual_staffing", ()) if (row["room_id"], row["date"]) in keys]
