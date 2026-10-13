"""Read-only views of the historical room bookings: one room over a period, and one booked exam with all its rooms.

Nothing here runs or needs an optimisation. It reads the prepared booking data directly (`bookings.csv`, with the room
register `room_inventory.csv` for capacities and `candidate_linkage.csv` for the provisional link to Ladok) and answers:

* which places (address and room) have bookings, and over which dates (`locations_payload`);
* what is booked in one place in a date range (`location_payload`): the bookings, and measures with their definitions;
* which booked exams match a search (`search_exams`) and everything about one booked exam (`exam_payload`).

The grain is the booking *placement* (one row: an exam order in one place at one time with a number of booked places).
It is neither the exam need (Ladok) nor measured attendance. What the data cannot say is stated, never filled in:

* a booking without a named room is only *identified* to its address (`resource_identification = address_only`). Why the room is missing is not
  known and not assumed; its seats are not set against a room and it is never counted as a room;
* a booking has no measured attendance, so the utilisation of attendance is `unknown`, not zero;
* what a room could have been booked is not documented, so booked time is reported as time, without a share of "available".
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .booking_quality import QualityConfig, classify, load_config
from .booking_quality.config import DEFAULT_COLUMNS

BOOKINGS_FILE, ROOMS_FILE = "bookings.csv", "room_inventory.csv"
NO_ADDRESS = "Adress saknas"
# How firm the link from a booking to a Ladok activity is (`link_certainty` of the data quality layer), in words.
LINK_TEXT = {
    "unique": "En trolig koppling till en Ladok-aktivitet (provisorisk).",
    "ambiguous": "Flera möjliga Ladok-aktiviteter: kopplingen är tvetydig.",
    "none_within_coverage": "Ingen koppling hittad trots att Ladok-underlaget täcker datumet.",
    "none_outside_coverage": "Datumet ligger utanför Ladok-underlagets period, så ingen koppling kan finnas.",
    "none_coverage_unknown": "Ingen koppling hittad och Ladok-täckningen för datumet är okänd.",
    "not_assessed": "Kopplingen är inte bedömd (kopplingsunderlag saknas).",
}
# Links that a reader should treat with care. A link that cannot exist because Ladok does not cover the date is not unclear, it is not applicable.
UNCLEAR_LINKS = ("ambiguous", "none_within_coverage", "none_coverage_unknown")
IDENTIFICATION_TEXT = {
    "room_matched": "Sal identifierad i salsregistret.",
    "room_named_not_in_register": "Sal namngiven men saknas i salsregistret.",
    "address_only": "Bara adress angiven; sal saknas i uttaget (orsaken är okänd).",
    "no_address": "Adress saknas.",
    "declared_non_physical": "Ingen fysisk sal enligt en verifierad regel.",
}
MEASURES = {
    "booked_time": "Bokad tid: unionen av klockslagen som bokningarna täcker per dag (överlappande bokningar räknas en gång). Avbokade bokningar ingår inte.",
    "booked_places": "Bokade platser: summan av bokat antal platser. Det är det som bokades, inte antalet som kom.",
    "seat_share": "Bokade platser ÷ salens kapacitet, per bokning och som högsta samtidiga bokning. Kräver namngiven sal med känd kapacitet.",
    "attendance": "Verklig närvaro finns inte i underlaget och är därför okänd (inte noll).",
}


class BookingDataMissing(FileNotFoundError):
    """The prepared booking data is not there."""


def read_csv(processed_dir: Path, name: str) -> pd.DataFrame | None:
    path = processed_dir / name
    if not path.is_file():
        return None
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def place_label(address: str, room: str, identification: str) -> str:
    """A place in words, from what the data identifies. A missing room is stated as a fact about the extract, not explained."""
    if identification == "no_address":
        return NO_ADDRESS
    if identification == "address_only":
        return f"{address} (sal saknas i uttaget)"
    if identification == "room_named_not_in_register":
        return f"{address} – {room} (saknas i salsregistret)"
    if identification == "declared_non_physical":
        return f"{address} – {room} (ej fysisk sal enligt verifierad regel)" if room else f"{address} (ej fysisk lokal enligt verifierad regel)"
    return f"{address} – {room}"


def load_bookings(processed_dir: Path, config: QualityConfig | None = None) -> pd.DataFrame:
    """Booking rows with parsed times and the four dimensions of the data quality layer. Column names follow the configuration."""
    config = config or load_config()
    raw = read_csv(processed_dir, BOOKINGS_FILE)
    if raw is None:
        raise BookingDataMissing("Bokningsunderlaget är inte förberett. Förbered underlaget under Underlag först.")
    classified = classify(raw, config, read_csv(processed_dir, config.register["file"]), read_csv(processed_dir, config.linkage["file"]),
                          read_csv(processed_dir, config.coverage.get("file", "ladok_activities.csv")))
    frame = raw.rename(columns={config.columns[key]: name for key, name in DEFAULT_COLUMNS.items() if config.columns[key] != name}).copy()
    times = frame["scheduled_time"].str.extract(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$").astype("Int64")
    frame["start_min"] = times[0] * 60 + times[1]
    frame["end_min"] = times[2] * 60 + times[3]
    frame["places"] = pd.to_numeric(frame["booked_places"], errors="coerce").fillna(0).astype(int)
    frame["cancelled"] = classified["status_class"] == "cancelled"
    frame["status_class"] = classified["status_class"]
    frame["identification"] = classified["resource_identification"]
    frame["flags"] = classified["flags"]
    frame["ladok_coverage"] = classified["ladok_coverage"]
    frame["link"] = classified["link_certainty"]
    frame["candidate_rule_ids"] = classified["candidate_rule_ids"]
    # A capacity belongs to an identified room (the layer gives it only then): a booking that names only an address may be spread over several rooms.
    frame["capacity"] = pd.to_numeric(classified["capacity"], errors="coerce")
    return frame


def clock(minutes: Any) -> str | None:
    return None if pd.isna(minutes) else f"{int(minutes) // 60:02d}:{int(minutes) % 60:02d}"


def booking_item(row: pd.Series) -> dict[str, Any]:
    capacity = None if pd.isna(row["capacity"]) else int(row["capacity"])
    return {
        "placement_id": row["placement_id"], "exam_order_id": row["exam_order_id"], "course_codes": row["course_codes"],
        "course_name": row["course_name"], "exam_type": row["exam_type"], "date": row["scheduled_date"] or None,
        "start": clock(row["start_min"]), "end": clock(row["end_min"]),
        "address": row["address"] or None, "room": row["room"] or None, "location_key": row["location_key"] or None,
        "booked_places": int(row["places"]), "capacity": capacity,
        "seat_share": round(int(row["places"]) / capacity, 3) if capacity else None,
        "status": row["status"], "cancelled": bool(row["cancelled"]), "digital": row["digital_exam"] or None,
        "place_label": place_label(row["address"], row["room"], row["identification"]),
        "status_class": row["status_class"], "identification": row["identification"], "identification_text": IDENTIFICATION_TEXT[row["identification"]],
        "flags": list(row["flags"]), "ladok_coverage": row["ladok_coverage"],
        "link_certainty": row["link"], "link_text": LINK_TEXT.get(row["link"], LINK_TEXT["not_assessed"]),
    }


def coverage_payload(processed_dir: Path) -> dict[str, Any]:
    """What the booking data covers; missing dates and cancelled bookings are counted, not hidden."""
    frame = load_bookings(processed_dir)
    dated = frame[frame["scheduled_date"] != ""]
    return {"first": dated["scheduled_date"].min(), "last": dated["scheduled_date"].max(), "rows": int(len(frame)),
            "without_date": int(len(frame) - len(dated)), "cancelled": int(frame["cancelled"].sum()),
            "source": "Lokalbokningar", "measures": MEASURES,
            "attendance": {"available": False, "note": MEASURES["attendance"]}}


def locations_payload(processed_dir: Path) -> dict[str, Any]:
    """The places that have bookings: room level where a room is named, otherwise the address."""
    everything = load_bookings(processed_dir)
    frame = everything[(everything["location_key"] != "") & ~everything["cancelled"] & (everything["scheduled_date"] != "")]
    rows = []
    for key, group in frame.groupby("location_key"):
        room = group["room"].iloc[0]
        capacity = group["capacity"].dropna()
        rows.append({"location_key": key, "address": group["address"].iloc[0], "room": room or None, "identification": group["identification"].iloc[0],
                     "label": place_label(group["address"].iloc[0], room, group["identification"].iloc[0]),
                     "capacity": int(capacity.iloc[0]) if len(capacity) else None, "bookings": int(len(group)),
                     "first": group["scheduled_date"].min(), "last": group["scheduled_date"].max()})
    rows.sort(key=lambda item: (item["address"], item["room"] or "~"))
    return {"locations": rows, "addresses": address_rows(everything), "coverage": coverage_payload(processed_dir)}


def address_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Every address with bookings, whether or not a room is named. Rows without an address are one entry of their own, never dropped."""
    live = frame[~frame["cancelled"] & (frame["scheduled_date"] != "")]
    rows = []
    for address, group in live.groupby("address"):
        rows.append({"address": address, "label": address or NO_ADDRESS, "bookings": int(len(group)), "exam_orders": int(group["exam_order_id"].nunique()),
                     "named_rooms": int(group.loc[group["room"] != "", "room"].nunique()), "address_only_bookings": int((group["identification"] == "address_only").sum()),
                     "first": group["scheduled_date"].min(), "last": group["scheduled_date"].max()})
    rows.sort(key=lambda item: (item["address"] == "", item["address"]))
    return rows


def union_minutes(intervals: list[tuple[int, int]]) -> int:
    total, end = 0, -1
    for first, last in sorted(intervals):
        if first > end:
            total += last - first
            end = last
        elif last > end:
            total += last - end
            end = last
    return total


def peak_places(rows: pd.DataFrame) -> int:
    """The highest number of booked places at one moment (all rows are of one place and one day, or one range)."""
    events = sorted([(int(r.start_min), int(r.places)) for r in rows.itertuples()] + [(int(r.end_min), -int(r.places)) for r in rows.itertuples()],
                    key=lambda pair: (pair[0], pair[1]))
    peak = current = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def quality_summary(rows: pd.DataFrame) -> dict[str, Any]:
    """What the data quality layer found in some rows: identification and findings, as counts. Descriptions only, no interpretation."""
    flags = pd.Series([flag for items in rows["flags"] for flag in items], dtype=str).value_counts()
    return {"identification": {name: int(count) for name, count in rows["identification"].value_counts().items()},
            "flags": {name: int(count) for name, count in flags.items()},
            "unverified_rule_matches": {name: int(count) for name, count in pd.Series([i for ids in rows["candidate_rule_ids"] for i in ids], dtype=str).value_counts().items()}}


def quality_notes(live: pd.DataFrame, capacity: int | None, peak: int) -> list[str]:
    """Words for the findings that change how a reader should take the numbers. The cause of a missing room is never given."""
    notes = []
    identification = set(live["identification"])
    if "address_only" in identification:
        notes.append("Bokningarna anger bara adress (sal saknas i uttaget). Orsaken är okänd och ingen sal har antagits, så platser kan inte sättas mot en salskapacitet.")
    if "room_named_not_in_register" in identification:
        notes.append("Salen är namngiven men finns inte i salsregistret, så dess kapacitet är okänd.")
    elif capacity is None and "room_matched" in identification:
        notes.append("Salen finns i salsregistret men saknar kapacitetsuppgift, så platser kan inte sättas mot kapacitet.")
    exceed = int(sum("places_exceed_capacity" in flags for flags in live["flags"]))
    if exceed:
        notes.append(f"{exceed} bokningar har fler bokade platser än salens kapacitet i salsregistret. Det är flaggat som misstänkt data (kapacitetsuppgiften eller bokningen kan vara fel); inget är ändrat.")
    elif capacity is not None and peak > capacity:
        notes.append("Högsta samtidiga bokning överstiger salens kapacitet. Kapacitetsuppgiften eller bokningarna behöver kontrolleras.")
    return notes


def location_payload(processed_dir: Path, location_key: str, first: date, last: date) -> dict[str, Any]:
    """Bookings of one place in a date range, with measures that carry their definitions."""
    if first > last:
        raise ValueError("Startdatum får inte vara senare än slutdatum.")
    frame = load_bookings(processed_dir)
    coverage = coverage_payload(processed_dir)
    place = frame[frame["location_key"] == location_key]
    if place.empty:
        raise ValueError(f"Okänd lokal: {location_key}.")
    notes = []
    if last.isoformat() < coverage["first"] or first.isoformat() > coverage["last"]:
        notes.append(f"Perioden ligger utanför bokningsunderlaget, som täcker {coverage['first']}–{coverage['last']}.")
    elif first.isoformat() < coverage["first"] or last.isoformat() > coverage["last"]:
        notes.append(f"Delar av perioden ligger utanför bokningsunderlaget ({coverage['first']}–{coverage['last']}). Där är lokalen okänd, inte tom.")
    inside = place[(place["scheduled_date"] >= first.isoformat()) & (place["scheduled_date"] <= last.isoformat())]
    inside = inside.sort_values(["scheduled_date", "start_min", "placement_id"])
    live = inside[~inside["cancelled"]]
    days: dict[str, dict[str, Any]] = {}
    for day, group in live.groupby("scheduled_date"):
        timed = group.dropna(subset=["start_min", "end_min"])
        days[day] = {"bookings": int(len(group)), "booked_minutes": union_minutes(list(zip(timed["start_min"].astype(int), timed["end_min"].astype(int)))),
                     "booked_places": int(group["places"].sum()), "peak_places": peak_places(timed) if len(timed) else 0}
    capacity = place["capacity"].dropna()
    capacity_value = int(capacity.iloc[0]) if len(capacity) else None
    peak = max((day["peak_places"] for day in days.values()), default=0)
    summary = {"bookings": int(len(live)), "cancelled_bookings": int(inside["cancelled"].sum()), "exam_orders": int(live["exam_order_id"].nunique()),
               "days_with_bookings": len(days), "booked_minutes": sum(day["booked_minutes"] for day in days.values()),
               "booked_places": int(live["places"].sum()), "capacity": capacity_value,
               "peak_places": peak, "peak_share_of_capacity": round(peak / capacity_value, 3) if capacity_value else None,
               "untimed_bookings": int(live["start_min"].isna().sum())}
    notes += quality_notes(live, capacity_value, peak)
    first_row = place.iloc[0]
    return {"location": {"location_key": location_key, "address": first_row["address"] or None, "room": first_row["room"] or None},
            "date_from": first.isoformat(), "date_to": last.isoformat(), "bookings": [booking_item(row) for _, row in inside.iterrows()],
            "days": days, "summary": summary, "data_quality": quality_summary(live), "attendance": coverage["attendance"], "measures": MEASURES,
            "coverage": coverage, "notes": notes}


def search_exams(processed_dir: Path, query: str, first: date | None = None, last: date | None = None, limit: int = 50) -> dict[str, Any]:
    """Booked exams (orders) whose id, course code or course name contains `query`, optionally within a date range."""
    frame = load_bookings(processed_dir)
    text = query.strip().lower()
    if not text and first is None and last is None:
        raise ValueError("Ange ett sökord (id, kurskod eller kursnamn) eller ett datumintervall.")
    mask = pd.Series(True, index=frame.index)
    if text:
        mask &= (frame["exam_order_id"].str.lower().str.contains(text, regex=False) | frame["course_codes"].str.lower().str.contains(text, regex=False)
                 | frame["course_name"].str.lower().str.contains(text, regex=False))
    if first is not None:
        mask &= frame["scheduled_date"] >= first.isoformat()
    if last is not None:
        mask &= frame["scheduled_date"] <= last.isoformat()
    hits = frame[mask & (frame["scheduled_date"] != "")]
    orders = []
    for order_id, group in hits.groupby("exam_order_id"):
        live = group[~group["cancelled"]]
        shown = live if len(live) else group
        orders.append({"exam_order_id": order_id, "course_codes": group["course_codes"].iloc[0], "course_name": group["course_name"].iloc[0],
                       "first_date": shown["scheduled_date"].min(), "last_date": shown["scheduled_date"].max(), "placements": int(len(group)),
                       "rooms": int(shown["location_key"].nunique()), "booked_places": int(live["places"].sum()), "all_cancelled": bool(len(live) == 0)})
    orders.sort(key=lambda item: (item["first_date"], item["exam_order_id"]))
    return {"query": query, "total": len(orders), "truncated": len(orders) > limit, "exams": orders[:limit]}


def exam_payload(processed_dir: Path, order_id: str) -> dict[str, Any]:
    """One booked exam: every placement (room, time, booked places), and how firm the link to Ladok is."""
    frame = load_bookings(processed_dir)
    rows = frame[frame["exam_order_id"] == order_id].sort_values(["scheduled_date", "start_min", "placement_id"])
    if rows.empty:
        raise ValueError(f"Okänd tentamensbokning: {order_id}.")
    live = rows[~rows["cancelled"]]
    links = sorted(set(rows["link"]))
    return {"exam_order_id": order_id, "course_codes": rows["course_codes"].iloc[0], "course_name": rows["course_name"].iloc[0],
            "exam_type": rows["exam_type"].iloc[0], "placements": [booking_item(row) for _, row in rows.iterrows()],
            "booked_places": int(live["places"].sum()), "rooms": int(live["location_key"].nunique()),
            "link_certainties": links, "link_unclear": any(item in UNCLEAR_LINKS for item in links),
            "link_texts": [LINK_TEXT[item] for item in links], "data_quality": quality_summary(live),
            "attendance": {"available": False, "note": MEASURES["attendance"]}}
