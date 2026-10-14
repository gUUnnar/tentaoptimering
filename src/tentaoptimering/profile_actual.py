"""A – the actual booking: what was booked for the exams of a scope, reproduced as it is, with no optimisation.

This reads the prepared booking data and nothing else. Every exam keeps the date, time, rooms and booked places it
was given in the bookings, even if that booking is inefficient, uses rooms that are not in the room register of the
optimisation model, or could not be recreated by the engine. Where the data is thin it says so (`quality`), it never
turns an unknown into a number:

* a booking that names only an address is listed under its address and is not set against a room's capacity;
* a room that is named but has no capacity in the register is counted as used, with unknown capacity;
* a "place" that is not physical (for example "Hemma") is shown, but is not a room and has no capacity;
* booked places (what was reserved) are not participants (what Ladok registered): both are shown, and never merged.

The result has the same shape as the profile of a saved run (`profile_run`), so that the two can be compared.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .booking_views import clock, load_bookings, place_label
from .profile_common import room_usage, utilization
from .joint_selection import READY_STATUS
from .wishes import RANKS, WISHES_FILE, date_rank

ACTUAL = "actual"
EVENTS_FILE, DEMANDS_FILE, ROOMS_FILE, INVENTORY_FILE = "exam_events.csv", "optimization_demands.csv", "optimization_rooms.csv", "room_inventory.csv"


def _read(processed_dir: Path, name: str) -> pd.DataFrame | None:
    path = processed_dir / name
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False) if path.is_file() else None


def scope_event_ids(processed_dir: Path, plan_area: str, date_from: str | None, date_to: str | None) -> list[str]:
    """The exam events that are ready for modelling in a plan area, optionally within a date range (by booked date)."""
    demands = _read(processed_dir, DEMANDS_FILE)
    if demands is None:
        raise FileNotFoundError("Underlaget är inte förberett. Förbered underlaget under Underlag först.")
    ready = demands[(demands["demand_input_status"] == READY_STATUS) & (demands["observed_cities"] == plan_area)]
    if date_from:
        ready = ready[ready["scheduled_date"] >= date_from]
    if date_to:
        ready = ready[ready["scheduled_date"] <= date_to]
    return sorted(set(ready["exam_event_id"]))


def _place(row: Any, rooms: dict[str, dict[str, Any]], model_rooms: set[str]) -> dict[str, Any]:
    info = rooms.get(row.location_key, {})
    physical = row.identification in ("room_matched", "room_named_not_in_register")  # an address or a non-physical place is not a room
    capacity = None if pd.isna(row.capacity) else int(row.capacity)
    return {"label": place_label(row.address, row.room, row.identification), "address": row.address or None, "room": row.room or None,
            "room_id": (info.get("room_id") or None) if physical else None, "capacity": capacity, "booked_places": int(row.places), "identification": row.identification,
            "in_model_register": bool(physical and info.get("room_id") and info["room_id"] in model_rooms)}


def actual_profile(processed_dir: Path, event_ids: list[str], label: str = "A – Faktisk bokning") -> dict[str, Any]:
    """The actual booking of the given exam events. Events are the optimisation demand's grain (one per booked exam occasion)."""
    events, demands, wishes = _read(processed_dir, EVENTS_FILE), _read(processed_dir, DEMANDS_FILE), _read(processed_dir, WISHES_FILE)
    if events is None or demands is None:
        raise FileNotFoundError("Underlaget är inte förberett. Förbered underlaget under Underlag först.")
    bookings = load_bookings(processed_dir)
    inventory = _read(processed_dir, INVENTORY_FILE)
    rooms = {row["location_key"]: {"room_id": row["room_id"]} for row in inventory.to_dict("records") if row["location_key"]} if inventory is not None else {}
    model = _read(processed_dir, ROOMS_FILE)
    model_rooms = set(model["room_id"]) if model is not None else set()
    wanted = set(event_ids)
    ready = demands[(demands["demand_input_status"] == READY_STATUS) & demands["exam_event_id"].isin(wanted)].copy()
    ready["demand_value"] = pd.to_numeric(ready["demand_value"], errors="coerce").fillna(0)
    per_event = ready.groupby("exam_event_id").agg(participants=("demand_value", "sum"), course=("course_code", lambda s: ", ".join(sorted(set(s)))),
                                                 exam_type=("observed_exam_types", "first"))
    wish_of = {row["exam_event_id"]: row for row in wishes.to_dict("records")} if wishes is not None else {}
    keyed = {(g[0], g[1], g[2]): rows for g, rows in bookings.groupby(["exam_order_id", "scheduled_date", "scheduled_time"])}
    exams: list[dict[str, Any]] = []
    for event in events[events["exam_event_id"].isin(wanted)].to_dict("records"):
        rows = keyed.get((event["exam_order_id"], event["scheduled_date"], event["scheduled_time"]))
        live = rows[~rows["cancelled"]] if rows is not None else None
        booked = live is not None and len(live) > 0 and event["scheduled_date"] != ""
        info = per_event.loc[event["exam_event_id"]] if event["exam_event_id"] in per_event.index else None
        wish = wish_of.get(event["exam_event_id"])
        wish_dates = [wish[key] or None for key in ("requested_date", "reserve_date_1", "reserve_date_2")] if wish else [None, None, None]
        exam: dict[str, Any] = {
            "exam_event_id": event["exam_event_id"], "exam_order_id": event["exam_order_id"], "course": None if info is None else info["course"],
            "exam_type": None if info is None else info["exam_type"], "participants": None if info is None else int(info["participants"]),
            "status": "booked" if booked else "not_booked",
            "not_booked_reason": None if booked else "Bokningen är avbokad eller saknar datum" + (f" (status: {event['booking_statuses']})." if event.get("booking_statuses") else "."),
            "wish": {"dates": wish_dates, "status": wish["wish_status"] if wish else "not_loaded", "reason": (wish["no_reserve_date_reason"] or None) if wish else None},
            "date": None, "start": None, "end": None, "places": [], "booked_places": 0, "quality": [],
        }
        if booked:
            first = live.sort_values(["start_min", "placement_id"]).iloc[0]
            exam.update(date=event["scheduled_date"], start=clock(first["start_min"]), end=clock(live["end_min"].max()),
                        places=[_place(row, rooms, model_rooms) for row in live.itertuples()], booked_places=int(live["places"].sum()))
            exam["wish"]["rank"] = date_rank(event["scheduled_date"], tuple(wish_dates)) if wish else "unknown"  # type: ignore[arg-type]
            exam["quality"] = sorted({flag for flags in live["flags"] for flag in flags} | {f"identification:{row.identification}" for row in live.itertuples() if row.identification != "room_matched"})
        exams.append(exam)
    return _profile(label, exams, wanted)


def _profile(label: str, exams: list[dict[str, Any]], wanted: set[str]) -> dict[str, Any]:
    booked = [item for item in exams if item["status"] == "booked"]
    named = {(p["address"], p["room"]): p for item in booked for p in item["places"] if p["room"] and p["identification"] in ("room_matched", "room_named_not_in_register")}
    in_model = {key for key, p in named.items() if p["in_model_register"]}
    address_only = {p["address"] for item in booked for p in item["places"] if p["identification"] == "address_only"}
    non_physical = {p["label"] for item in booked for p in item["places"] if p["identification"] == "declared_non_physical"}
    items = _seat_items(booked)
    rank_counts = {rank: sum(1 for item in booked if item["wish"].get("rank") == rank) for rank in RANKS}
    rank_counts["unknown"] = sum(1 for item in booked if item["wish"].get("rank", "unknown") == "unknown")
    notes = []
    if len(named) > len(in_model):
        notes.append(f"{len(named) - len(in_model)} av de {len(named)} namngivna salarna i bokningen finns inte i optimeringsmodellens lokalregister. Bokningen visas ändå fullt ut; jämförelser med körningar gäller bara det som går att jämföra.")
    if address_only:
        notes.append(f"Bokningar på {len(address_only)} adresser anger bara adress, inte sal. De räknas inte som salar och sätts inte mot någon kapacitet.")
    return {
        "ref": ACTUAL, "kind": "A", "name": label, "available": True, "unavailable_reason": None, "exams": exams,
        "scope": {"exam_count": len(wanted), "booked": len(booked), "not_booked": len(exams) - len(booked),
                  "participants": sum(item["participants"] or 0 for item in exams), "booked_places": sum(item["booked_places"] for item in booked)},
        "metrics": {"rooms_used": len(named), "rooms_in_model_register": len(in_model), "rooms_outside_model_register": len(named) - len(in_model),
                    "addresses_without_room": len(address_only), "non_physical_places": len(non_physical), "staff_pool": None},
        "wish_distribution": rank_counts, "room_usage": room_usage(items), "utilization": utilization(items, _exams_per_day(booked)),
        "unplaced": [{"exam_event_id": item["exam_event_id"], "course": item["course"], "reason": item["not_booked_reason"]} for item in exams if item["status"] != "booked"],
        "cost": {"kind": "historical", "available": False,
                 "note": "Bokningsunderlaget innehåller inga kostnader per tentamen eller sal. Faktisk kostnad finns bara som preliminär intern hyra för hela tentamenslokalverksamheten (lease_rows) och går inte att fördela på ett urval."},
        "notes": notes,
    }


def _minutes(clock_text: str | None) -> int | None:
    return None if not clock_text else int(clock_text[:2]) * 60 + int(clock_text[3:5])


def _seat_items(booked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Booked places per place and time. A booking without a parsable time cannot be placed on the clock and is left out of the time measures."""
    items = []
    for exam in booked:
        start, end = _minutes(exam["start"]), _minutes(exam["end"])
        if start is None or end is None:
            continue
        for place in exam["places"]:
            items.append({"date": exam["date"], "start_min": start, "end_min": end if end > start else end + 1440, "seats": place["booked_places"], "label": place["label"],
                          "room_id": place["room_id"], "kind": place["identification"], "capacity": place["capacity"], "in_model_register": place["in_model_register"]})
    return items


def _exams_per_day(booked: list[dict[str, Any]]) -> dict[str, int]:
    days: dict[str, int] = {}
    for exam in booked:
        days[exam["date"]] = days.get(exam["date"], 0) + 1
    return days
