"""Overview of historical bookings for a day or a period, per address and room, without any optimisation run.

Answers: which places were booked, for which exams, and to what extent, for a chosen period (and optionally one address).

How the counting is kept honest:

* The grain is the booking placement. A booking that names only an address stays in its own row ("sal saknas i uttaget") under that
  address; it is never assigned to a room, and it is never dropped. A booking without an address is one entry of its own.
* An exam that uses several rooms is counted **once** in every total (`exam_orders`) and once in each place it uses. The place
  rows therefore may add up to more than the total, which `notes` says. Booked places are seats and do add up.
* Booked time (union of clock times, overlap counted once), booked places and attendance are separate measures; attendance is
  not in the data and is `unknown`, never zero. Cancelled bookings are counted apart and are not in the sums.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .booking_views import (
    MEASURES, NO_ADDRESS, booking_item, coverage_payload, load_bookings, peak_places, place_label, quality_summary, union_minutes,
)

EXAM_LIMIT = 300
MULTI_PLACE_NOTE = ("En tentamen som använder flera lokaler räknas en gång i totalen men i varje lokal den använder, "
                    "så summan av raderna kan överstiga totalen. Bokade platser är platser och summeras.")


def _measures(group: pd.DataFrame) -> dict[str, Any]:
    """The measures of the active (not cancelled) rows of one place or address."""
    live = group[~group["cancelled"]]
    minutes = 0
    peak = 0
    for _, day in live.dropna(subset=["start_min", "end_min"]).groupby("scheduled_date"):
        minutes += union_minutes(list(zip(day["start_min"].astype(int), day["end_min"].astype(int))))
        peak = max(peak, peak_places(day))
    return {"placements": int(len(live)), "cancelled_placements": int(group["cancelled"].sum()), "exam_orders": int(live["exam_order_id"].nunique()),
            "booked_places": int(live["places"].sum()), "booked_minutes": minutes, "peak_places": peak,
            "untimed_placements": int(live["start_min"].isna().sum())}


def _room_rows(group: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for room, part in group.groupby("room"):
        capacity = part["capacity"].dropna()
        values = _measures(part)
        cap = int(capacity.iloc[0]) if len(capacity) else None
        rows.append({"room": room or None, "label": place_label(part["address"].iloc[0], room, part["identification"].iloc[0]), "identification": part["identification"].iloc[0], "location_key": part["location_key"].iloc[0] or None,
                     "capacity": cap, "peak_share_of_capacity": round(values["peak_places"] / cap, 3) if cap else None, **values})
    rows.sort(key=lambda item: (item["room"] is None, item["room"] or ""))
    return rows


def _exam_rows(live: pd.DataFrame) -> tuple[list[dict[str, Any]], int]:
    rows = []
    for order_id, group in live.groupby("exam_order_id"):
        places = [{"label": place_label(r.address, r.room, r.identification), "identification": r.identification, "address": r.address or None, "room": r.room or None, "booked_places": int(r.places)}
                  for r in group.itertuples()]
        rows.append({"exam_order_id": order_id, "course_codes": group["course_codes"].iloc[0], "course_name": group["course_name"].iloc[0],
                     "exam_type": group["exam_type"].iloc[0], "first_date": group["scheduled_date"].min(), "last_date": group["scheduled_date"].max(),
                     "booked_places": int(group["places"].sum()), "places": places, "place_count": len({item["label"] for item in places})})
    rows.sort(key=lambda item: (item["first_date"], item["course_codes"], item["exam_order_id"]))
    return rows[:EXAM_LIMIT], len(rows)


def overview_payload(processed_dir: Path, first: date, last: date, address: str | None = None) -> dict[str, Any]:
    """Bookings in a period, per address and room; with `address` also all bookings there for a timeline."""
    if first > last:
        raise ValueError("Startdatum får inte vara senare än slutdatum.")
    frame = load_bookings(processed_dir)
    coverage = coverage_payload(processed_dir)
    notes = []
    if last.isoformat() < coverage["first"] or first.isoformat() > coverage["last"]:
        notes.append(f"Perioden ligger utanför bokningsunderlaget, som täcker {coverage['first']}–{coverage['last']}.")
    elif first.isoformat() < coverage["first"] or last.isoformat() > coverage["last"]:
        notes.append(f"Delar av perioden ligger utanför bokningsunderlaget ({coverage['first']}–{coverage['last']}). Där är bokningarna okända, inte frånvarande.")
    scope = frame[(frame["scheduled_date"] >= first.isoformat()) & (frame["scheduled_date"] <= last.isoformat()) & (frame["scheduled_date"] != "")]
    if address is not None:
        if address not in set(frame["address"]) or (address == "" and not len(frame[frame["address"] == ""])):
            raise ValueError(f"Okänd adress: {address or NO_ADDRESS}.")
        scope = scope[scope["address"] == address]
    live = scope[~scope["cancelled"]]
    addresses = []
    for name, group in scope.groupby("address"):
        values = _measures(group)
        named = group[group["room"] != ""]
        addresses.append({"address": name, "label": name or NO_ADDRESS, **values, "named_rooms": int(named["room"].nunique()),
                          "address_only_placements": int(((group["identification"] == "address_only") & ~group["cancelled"]).sum()), "rooms": _room_rows(group)})
    addresses.sort(key=lambda item: (item["address"] == "", -item["booked_places"], item["address"]))
    exams, exam_total = _exam_rows(live)
    several = int((live.groupby("exam_order_id").apply(lambda g: len({(a, r) for a, r in zip(g["address"], g["room"])}), include_groups=False) > 1).sum()) if len(live) else 0
    totals = {"placements": int(len(live)), "cancelled_placements": int(scope["cancelled"].sum()), "exam_orders": int(live["exam_order_id"].nunique()),
              "booked_places": int(live["places"].sum()), "addresses": int(live["address"].replace("", pd.NA).nunique()),
              "no_address_placements": int((live["identification"] == "no_address").sum()), "address_only_placements": int((live["identification"] == "address_only").sum()),
              "exam_orders_in_several_places": several}
    if len(live):
        notes.append(MULTI_PLACE_NOTE)
    if totals["address_only_placements"]:
        notes.append(f"{totals['address_only_placements']} bokningar anger bara adress (sal saknas i uttaget). De visas under sin adress, ingår i alla summor och har inte hänförts till någon sal. "
                     "Orsaken till att sal saknas är okänd och har inte antagits.")
    quality = quality_summary(live)
    unverified = quality["unverified_rule_matches"]
    if unverified:
        notes.append("Vissa rader liknar mönster som dataägaren inte bekräftat ännu (" + ", ".join(f"{name}: {count}" for name, count in unverified.items()) + "). De är inte omklassade.")
    return {"date_from": first.isoformat(), "date_to": last.isoformat(), "address": address, "totals": totals, "addresses": addresses,
            "exams": exams, "exams_total": exam_total, "exams_truncated": exam_total > len(exams),
            "bookings": [booking_item(row) for _, row in scope.sort_values(["scheduled_date", "start_min", "placement_id"]).iterrows()] if address is not None else None,
            "data_quality": quality, "attendance": coverage["attendance"], "measures": MEASURES, "coverage": coverage, "notes": notes}
