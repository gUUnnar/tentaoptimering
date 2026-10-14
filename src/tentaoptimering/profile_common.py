"""Measures that are the same for the actual booking (A) and a saved run (B/C), computed from a list of seat items.

A *seat item* is one group of seats in one place for one stretch of time:
`{"date", "start_min", "end_min", "seats", "label", "room_id", "kind", "capacity", "in_model_register"}`.
`seats` are booked places for A and assigned participants for a run; the two are different measures and are named so by
the caller. `capacity` is None where the place has no known capacity (it is then never counted in a share).
"""

from __future__ import annotations

from typing import Any

from .booking_views import union_minutes


def peak_concurrent(items: list[dict[str, Any]]) -> int:
    """The highest number of seats in use at one moment (an item ending when another starts does not overlap)."""
    events = sorted([(item["start_min"], item["seats"]) for item in items] + [(item["end_min"], -item["seats"]) for item in items], key=lambda pair: (pair[0], pair[1]))
    peak = current = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def room_usage(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per place: sessions, time in use (overlaps counted once), highest simultaneous seats and its share of a known capacity."""
    places: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        places.setdefault(item["label"], []).append(item)
    rows = []
    for label, entries in places.items():
        first = entries[0]
        days: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            days.setdefault(entry["date"], []).append(entry)
        minutes = sum(union_minutes([(e["start_min"], e["end_min"]) for e in day]) for day in days.values())
        peak = max(peak_concurrent(day) for day in days.values())
        capacity = first["capacity"]
        rows.append({"label": label, "room_id": first["room_id"], "kind": first["kind"], "capacity": capacity, "in_model_register": first["in_model_register"],
                     "sessions": len(entries), "days": len(days), "booked_minutes": minutes, "peak_seats": peak,
                     "peak_share": round(peak / capacity, 3) if capacity else None})
    return sorted(rows, key=lambda row: (-row["sessions"], row["label"]))


def utilization(items: list[dict[str, Any]], exams_per_day: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """Per day: all seats, and the highest simultaneous seats in rooms of known capacity against the capacity of those rooms."""
    days: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        days.setdefault(item["date"], []).append(item)
    rows = []
    for day in sorted(days):
        entries = days[day]
        known = [e for e in entries if e["capacity"]]
        capacity = sum({e["label"]: e["capacity"] for e in known}.values())
        peak = peak_concurrent(known) if known else 0
        rows.append({"date": day, "exams": (exams_per_day or {}).get(day), "seats": sum(e["seats"] for e in entries), "rooms": len({e["label"] for e in entries}),
                     "capacity_known": capacity or None, "peak_seats_in_known_rooms": peak if known else None,
                     "share": round(peak / capacity, 3) if capacity else None})
    return rows
