"""Fixed bookings outside the optimised exams that block rooms (see `docs/PERIODVAL_OCH_SNABBA_KORNINGAR.md`).

The optimisation chooses dates and rooms for a selection of exams. Other bookings in the same rooms and days are not
the engine's to move, but they take the room: a plan that puts a selected exam in a room that is already booked is not a
plan. A *reservation* is such a booking, as the optimiser receives it: a room, a date and a time.

What blocks and what does not follows the data, never a guess:

* only a booking that identifies a room (`room_matched`, or a named room that the model has) blocks that room;
* a booking that names only an address, has no address or is not a physical place blocks nothing. Its bookings, places
  and time are counted and reported as *unidentified* so that the run says what it could not take into account;
* a cancelled booking and a booking without a date or a clock time block nothing and are not counted as unidentified;
* the exams of the selection are not reservations (they are placed by the optimiser), nor are bookings on dates the
  planning calendar does not contain.

A blocking reservation takes the whole room for its time plus the turnaround: the register has no finer unit than the room.
That is conservative; it is stated in the basis. `reservations.policy = none` ignores the bookings, and the run is marked.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .booking_views import BookingDataMissing, load_bookings, read_csv
from .joint_contract import CandidateSlot, Reservation, Room
from .joint_selection import READY_STATUS

POLICY_BLOCK = "block_identified"
POLICY_NONE = "none"
KEEP_FIXED, REMOVE = "keep_fixed", "remove"
# Why a booking is not among the optimised exams. Each group gets its own, explicit action; the careful default is to keep it fixed.
GROUPS = {
    "no_participant_count": ("Tentor utan deltagarantal", "Tentan finns i underlaget men saknar känt antal anmälda och är därför inte klar för modellering."),
    "outside_selection": ("Tentor utanför valt urval", "Tentan har känt antal men ingår inte i det valda urvalet eller den valda perioden."),
    "not_in_ladok": ("Bokningar utan tentamen i underlaget", "Bokningen saknar koppling till en tentamen i efterfrågeunderlaget (till exempel ”Extern”)."),
}
ACTION_PARAMETERS = {"no_participant_count": "reservations.action_no_count", "outside_selection": "reservations.action_outside_selection",
                     "not_in_ladok": "reservations.action_not_in_ladok"}
LIST_LIMIT = 500


def build_reservations(
    processed_dir: Path, population_event_ids: set[str], rooms: tuple[Room, ...], slots: tuple[CandidateSlot, ...], policy: str,
    actions: dict[str, str] | None = None,
) -> tuple[tuple[Reservation, ...], dict[str, Any]]:
    """The blocking reservations and a record of what was counted: `{policy, status, blocking, unidentified_*, ...}`."""
    actions = {group: (actions or {}).get(group, KEEP_FIXED) for group in GROUPS}
    basis: dict[str, Any] = {"policy": policy, "granularity": "whole_room_for_booked_time_plus_turnaround", "actions": actions}
    if policy == POLICY_NONE:
        return (), {**basis, "status": "ignored_by_parameter", "blocking": 0,
                    "note": "Fasta bokningar utanför de valda tentorna ignoreras enligt parametern. Körningen är explorativ."}
    if policy != POLICY_BLOCK:
        raise ValueError(f"Okänd policy för fasta bokningar: {policy}")
    try:
        bookings = load_bookings(processed_dir)
    except BookingDataMissing:
        return (), {**basis, "status": "bookings_unavailable", "blocking": 0, "note": "Bokningsunderlaget saknas; inga fasta bokningar kunde läsas."}
    events = read_csv(processed_dir, "exam_events.csv")
    inventory = read_csv(processed_dir, "room_inventory.csv")
    if events is None or inventory is None:
        return (), {**basis, "status": "bookings_unavailable", "blocking": 0, "note": "Bokningshändelser eller lokalinventering saknas."}
    demand_rows = read_csv(processed_dir, "optimization_demands.csv")
    status_of = {}
    if demand_rows is not None:
        for row in demand_rows.to_dict("records"):
            status_of[row["exam_event_id"]] = status_of.get(row["exam_event_id"], False) or row["demand_input_status"] == READY_STATUS
    days = {slot.scheduled_date for slot in slots}
    room_ids = {room.room_id for room in rooms}
    room_of = {row["location_key"]: row["room_id"] for row in inventory.to_dict("records") if row["location_key"] and row["room_id"]}
    event_of = {(row["exam_order_id"], row["scheduled_date"], row["scheduled_time"]): row["exam_event_id"] for row in events.to_dict("records")}
    reservations: list[Reservation] = []
    listing: list[dict[str, Any]] = []
    unidentified = {"bookings": 0, "booked_places": 0}
    outside_model = 0
    for row in bookings.to_dict("records"):
        if row["cancelled"] or not row["scheduled_date"] or pd.isna(row["start_min"]) or pd.isna(row["end_min"]):
            continue
        day = date.fromisoformat(row["scheduled_date"])
        if day not in days:
            continue
        event_id = event_of.get((row["exam_order_id"], row["scheduled_date"], row["scheduled_time"]))
        if event_id in population_event_ids:
            continue
        identified = row["identification"] in ("room_matched", "room_named_not_in_register")
        room_id = room_of.get(row["location_key"]) if identified else None
        if room_id is None:
            unidentified["bookings"] += 1
            unidentified["booked_places"] += int(row["places"])
            continue
        if room_id not in room_ids:
            outside_model += 1  # a named room the model does not have: it cannot be used by the model, so it cannot be blocked either
            continue
        end = int(row["end_min"]) if int(row["end_min"]) > int(row["start_min"]) else int(row["end_min"]) + 1440
        group = "not_in_ladok" if event_id not in status_of else "outside_selection" if status_of[event_id] else "no_participant_count"
        action = actions[group]
        listing.append({"reservation_id": str(row["placement_id"]), "group": group, "action": action, "date": row["scheduled_date"], "start_minute": int(row["start_min"]), "end_minute": end,
                        "room_id": room_id, "booked_places": int(row["places"]), "course": row["course_codes"], "exam_event_id": event_id})
        if action == REMOVE:
            continue  # an explicit choice of the user: this group blocks nothing, and the run says so
        reservations.append(Reservation(
            reservation_id=str(row["placement_id"]), room_id=room_id, scheduled_date=day, start_minute=int(row["start_min"]), end_minute=end,
            source_booking_id=str(row["placement_id"]), exam_event_id=event_id, basis=f"booked_{row['identification']}", group=group,
        ))
    chosen = tuple(sorted(reservations, key=lambda item: (item.scheduled_date, item.room_id, item.start_minute, item.reservation_id)))
    groups = [{"group": key, "label": GROUPS[key][0], "why": GROUPS[key][1], "action": actions[key], "action_parameter": ACTION_PARAMETERS[key],
               "bookings": sum(1 for item in listing if item["group"] == key), "booked_places": sum(item["booked_places"] for item in listing if item["group"] == key),
               "rooms": sorted({item["room_id"] for item in listing if item["group"] == key})} for key in GROUPS]
    return chosen, {
        **basis, "status": "read", "blocking": len(chosen), "removed": len(listing) - len(chosen), "groups": groups,
        "bookings": sorted(listing, key=lambda item: (item["date"], item["start_minute"], item["room_id"]))[:LIST_LIMIT], "bookings_truncated": len(listing) > LIST_LIMIT, "blocked_rooms": sorted({item.room_id for item in chosen}),
        "unidentified_bookings": unidentified["bookings"], "unidentified_booked_places": unidentified["booked_places"],
        "bookings_in_rooms_outside_model": outside_model,
        "note": ("Bokningar utan identifierad sal (bara adress, adress saknas eller ingen fysisk sal) spärrar ingenting och är okända till sin upptagenhet. "
                 "Salar spärras hela den tid bokningen gäller plus ställtid."),
    }
