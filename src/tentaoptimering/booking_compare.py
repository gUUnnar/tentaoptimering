"""Compare a booked exam (history) with its placement in a chosen joint run, read from the saved run files.

The two are different things and are kept apart: the booking is what was reserved (placements: room, time, booked places), the run
is a simulation of the exam need from Ladok (participants, date, start, assigned rooms). The only way from one to the other is the
provisional link between a booking placement and a Ladok activity (`candidate_linkage.csv`), so the comparison says how firm that
link is, and says nothing where there is none:

* no linked activity: `no_link`, with the reason; nothing is guessed from course code or date;
* linked activity that the run does not contain (outside its period, not ready for modelling): `not_in_run`;
* otherwise `compared`: original slot against the simulated slot, and booked rooms against the simulated rooms.

A room can be compared only where the booking names one; a booking that names only an address has its address listed and is
not set against a simulated room. Booked places (reserved seats) and participants (registered, from Ladok) are never merged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .app_storage import AppStorage
from .booking_quality import load_config
from .booking_views import LINK_TEXT, UNCLEAR_LINKS, load_bookings, place_label, read_csv

RESULT_FILE, INPUT_FILE = "joint_result.json", "joint_input.json"


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _slot(slot_id: str | None) -> dict[str, Any] | None:
    """`2026-01-16T14:00` as a date and a start time."""
    if not slot_id or "T" not in slot_id:
        return None
    day, clock = slot_id.split("T", 1)
    return {"date": day, "start": clock[:5], "slot_id": slot_id}


def _room_names(processed_dir: Path, config: Any) -> dict[str, dict[str, Any]]:
    """Room id to address, name and capacity, with the register's column names from the configuration."""
    reg = config.register
    rooms = read_csv(processed_dir, reg["file"])
    if rooms is None:
        return {}
    usable = rooms[rooms[reg["room_id"]] != ""]
    return {row[reg["room_id"]]: {"address": row[reg["address"]], "room": row[reg["room_name"]], "capacity": int(row[reg["capacity"]]) if row[reg["capacity"]].isdigit() else None}
            for row in usable.to_dict("records")}


def _days_between(first: str, last: str) -> int:
    return int((pd.Timestamp(last) - pd.Timestamp(first)).days)


def _no_link_reason(certainties: list[str]) -> dict[str, str]:
    """Why a booking has no linked Ladok activity, told apart by cause. Nothing is guessed from course code or date."""
    if set(certainties) == {"none_outside_coverage"}:
        return {"status": "no_link", "reason_code": "outside_ladok_coverage",
                "reason": "Bokningens datum ligger utanför Ladok-underlagets period, så ingen koppling kan finnas. Ingen koppling har gissats fram."}
    if "not_assessed" in certainties:
        return {"status": "no_link", "reason_code": "link_not_assessed", "reason": "Kopplingsunderlaget saknas, så bokningen kan inte sättas mot körningens tentamina."}
    if "none_coverage_unknown" in certainties:
        return {"status": "no_link", "reason_code": "coverage_unknown", "reason": "Ingen Ladok-aktivitet hittad och Ladok-täckningen för datumet är okänd. Ingen koppling har gissats fram."}
    return {"status": "no_link", "reason_code": "no_candidate_within_coverage",
            "reason": "Ingen Ladok-aktivitet hittades trots att Ladok-underlaget täcker datumet, så bokningen kan inte sättas mot körningens tentamina. Ingen koppling har gissats fram."}


def compare_payload(storage: AppStorage, order_id: str, run_id: str) -> dict[str, Any]:
    """The comparison of one booked exam with one run; `run_id` must name a saved run."""
    processed = storage.processed_dir
    frame = load_bookings(processed)
    rows = frame[frame["exam_order_id"] == order_id]
    if rows.empty:
        raise ValueError(f"Okänd tentamensbokning: {order_id}.")
    run_dir = storage.run_directory(run_id)
    result, problem = _json(run_dir / RESULT_FILE), _json(run_dir / INPUT_FILE)
    if not result or not problem:
        raise FileNotFoundError("Körningen har inget sparat resultat att jämföra med.")
    config = load_config()
    live = rows[~rows["cancelled"]]
    booking = [{"date": r.scheduled_date or None, "start": r.start_min, "label": place_label(r.address, r.room, r.identification), "identification": r.identification,
                "address": r.address or None, "room": r.room or None, "booked_places": int(r.places), "status": r.status, "cancelled": bool(r.cancelled)}
               for r in rows.itertuples()]
    for item, row in zip(booking, rows.itertuples()):
        item["start"] = None if pd.isna(row.start_min) else f"{int(row.start_min) // 60:02d}:{int(row.start_min) % 60:02d}"
        item["end"] = None if pd.isna(row.end_min) else f"{int(row.end_min) // 60:02d}:{int(row.end_min) % 60:02d}"
    cfg = config.linkage
    links = read_csv(processed, cfg["file"])
    mine = links[links[cfg["placement_id"]].isin(set(rows["placement_id"]))] if links is not None else pd.DataFrame(columns=[cfg["placement_id"], cfg["activity_id"]])
    statuses = sorted(set(rows["link"]))  # the layer's link certainty per placement, not the source's raw status
    activities = sorted({a for a in mine[cfg["activity_id"]] if a}) if len(mine) else []
    base = {"exam_order_id": order_id, "course_codes": rows["course_codes"].iloc[0], "course_name": rows["course_name"].iloc[0], "run_id": run_id,
            "problem_id": result.get("problem_id"), "booking": booking, "booked_places": int(live["places"].sum()),
            "link": {"certainties": statuses, "texts": [LINK_TEXT[item] for item in statuses], "activity_ids": activities,
                     "unclear": any(item in UNCLEAR_LINKS for item in statuses), "provisional": True},
            "run": {"outcome": (result.get("solver") or {}).get("outcome") if isinstance(result.get("solver"), dict) else None,
                    "technical_placement_complete": (result.get("coverage") or {}).get("technical_placement_complete")},
            "demands": [], "notes": []}
    if not activities:
        return {**base, **_no_link_reason(statuses)}
    wanted = set(activities)
    demands = [d for d in problem.get("demands", []) if isinstance(d, dict) and wanted & {a for g in d.get("participant_groups", []) for a in g.get("source_activity_ids", [])}]
    if not demands:
        return {**base, "status": "not_in_run", "reason": "Den kopplade Ladok-aktiviteten ingår inte i körningen (utanför körningens period, inte klar för modellering eller bortvald)."}
    schedule = {item["exam_demand_id"]: item for item in result.get("schedule", []) if isinstance(item, dict)}
    assigned: dict[str, list[dict[str, Any]]] = {}
    for item in result.get("assignments", []):
        assigned.setdefault(item["exam_demand_id"], []).append(item)
    names = _room_names(processed, config)
    booked_rooms = {(item["address"], item["room"]) for item in booking if not item["cancelled"] and item["room"]}
    booked_addresses = {item["address"] for item in booking if not item["cancelled"] and item["address"]}
    for demand in demands:
        key = demand["exam_demand_id"]
        entry = schedule.get(key, {})
        original, simulated = _slot(demand.get("original_slot_id")), _slot(entry.get("slot_id"))
        sim_rooms = [{"room_id": a["room_id"], "label": place_label(names.get(a["room_id"], {}).get("address", ""), names.get(a["room_id"], {}).get("room", ""), "room_matched") if a["room_id"] in names else a["room_id"],  # a simulated room comes from the register
                      "address": names.get(a["room_id"], {}).get("address"), "room": names.get(a["room_id"], {}).get("room"), "participants": int(a["participants"])}
                     for a in assigned.get(key, [])]
        sim_pairs = {(r["address"], r["room"]) for r in sim_rooms}
        unnamed = [item for item in booking if not item["cancelled"] and not item["room"]]
        base["demands"].append({
            "exam_demand_id": key, "course_code": demand.get("course_code"), "participants": sum(int(g["participant_count"]) for g in demand.get("participant_groups", [])),
            "duration_minutes": demand.get("duration_minutes"), "movable": bool(demand.get("movable")), "original": original, "simulated": simulated,
            "moved": bool(original and simulated and original["slot_id"] != simulated["slot_id"]),
            "date_shift_days": _days_between(original["date"], simulated["date"]) if original and simulated else None,
            "start_changed": bool(original and simulated and original["start"] != simulated["start"]),
            "simulated_rooms": sim_rooms,
            "rooms_compared": bool(booked_rooms) and not unnamed, "same_rooms": (booked_rooms == sim_pairs) if booked_rooms and not unnamed else None,
            "booked_rooms_without_name": len(unnamed),
            # Addresses can always be compared, also when a booking names no room.
            "booked_addresses": sorted(booked_addresses), "simulated_addresses": sorted({r["address"] for r in sim_rooms if r["address"]}),
            "same_addresses": bool(booked_addresses) and booked_addresses == {r["address"] for r in sim_rooms if r["address"]},
        })
    if len(demands) > 1:
        base["notes"].append(f"Bokningen motsvarar {len(demands)} tentamina i körningen (flera kopplade Ladok-aktiviteter).")
    if base["link"]["unclear"]:
        base["notes"].append("Kopplingen mellan bokning och Ladok är inte säker; jämförelsen gäller bara om den stämmer.")
    base["notes"].append("Bokade platser är reserverade platser; deltagare är anmälda enligt Ladok. De är olika mått och slås inte ihop.")
    return {**base, "status": "compared", "reason": None}
