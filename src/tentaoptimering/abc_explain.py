"""The saving between two alternatives, explained down to named rooms, changed bookings and paid staff hours.

Both alternatives are costed by one rule set (`abc_ledger`, `joint_pricing`), so the cost items of the two sides differ by
exactly what changed. The result keeps four things apart that must never be mixed:

* *model calculated* cost: what the rules give for a placement. A (the actual booking) has no historical cost per exam or room
  in the data; it is priced by the rules of the run it is compared with and says so;
* the split of the difference into *changed use of resources* (the same prices, a different plan) and *changed prices or
  assumptions* (the same plan, other prices). When the split cannot be made it says why;
* the *theoretical annual potential*, which needs an annualisation that the model does not have, so it is not computed;
* the *verified realisable saving*: only what the contract terms support, and never from simulated, assumed or calculated terms.

A comparison that would mislead is blocked with the reason: different exams, different underlay, changed demand, a booking that
cannot be priced. The item tables are still shown, marked incomplete, but no total difference is reported.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .abc_ledger import COST_KIND_ACTUAL, Ledger
from .cost_realization import classify_room, summarize
from .joint_pricing import COMPONENTS, PricedSession, price, pricing_signature, passes, reprice_staff

LIST_LIMIT = 200
ITEMS = (
    ("rooms", "Hyrda lokaler", ("annual_room_cost_ore",)),
    ("external", "Externa bokningar", ("external_room_session_cost_ore",)),
    ("staff", "Personal (betald tid)", ("staff_paid_time_cost_ore", "annual_staff_pool_cost_ore", "staff_session_cost_ore")),
)
PART_LABELS = {"staff_paid_time_cost_ore": "Betald personaltid", "annual_staff_pool_cost_ore": "Vaktpool", "staff_session_cost_ore": "Rörlig bemanning per salstillfälle"}
KIND_TEXT = {"model_calculated": "Modellberäknad kostnad", COST_KIND_ACTUAL: "Modellberäknad kostnad för de historiska bokningarna (inte faktisk kostnad)"}


def _kr(ore: int) -> str:
    return f"{round(abs(ore) / 100):,}".replace(",", " ") + " kr"


def _clock(minutes: int) -> str:
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def _sum(components: dict[str, int], names: tuple[str, ...]) -> int:
    return sum(components[name] for name in names)


def explain(left: Ledger, right: Ledger, labels: dict[str, str] | None = None) -> dict[str, Any]:
    """The explained comparison of `left` (reference) and `right`; see the module description."""
    labels = labels or {}
    reasons, notes = _blockers(left, right)
    split = _split(left, right)
    right_at_left = split.pop("_right_at_left", None)
    items = _items(left, right, right_at_left)
    rooms, freed, added = _rooms(left, right, labels)
    sessions = _sessions(left, right, labels)
    staff = _staffing(left, right)
    exams = _exams(left, right, freed, sessions)
    _drivers(items, rooms, sessions, staff, exams, labels)
    realization = _realization(left, right, rooms, sessions)
    difference = right.total - left.total
    available = not reasons
    if not available:
        split = _withhold(items, split)
    return {
        "available": available, "reasons": reasons, "notes": notes,
        "basis": _basis(left, right), "total": {"left_ore": left.total, "right_ore": right.total, "difference_ore": difference if available else None,
                                               "label": "Modellberäknad kostnad: lokaler som årskostnad, externhyra och personal för den valda perioden. Höger minus vänster."},
        "split": split, "items": items, "rooms": rooms, "added_rooms": added, "sessions": sessions, "staffing": staff, "exams": exams,
        "realization": realization, "savings_kinds": _kinds(difference if available else None, realization),
        "summary": _summary(left, right, items, difference) if available else None, "data_quality": _quality(left, right),
    }


def _withhold(items: list[dict[str, Any]], split: dict[str, Any]) -> dict[str, Any]:
    """A blocked comparison reports no cost difference at all, not even per item: the sides are not comparable."""
    for item in items:
        item.update(difference_ore=None, usage_ore=None, assumption_ore=None, drivers=[])
        for part in item.get("parts", ()):
            part["difference_ore"] = None
    return {"available": False, "reason": "Ingen uppdelning görs: totalskillnaden spärras eftersom underlaget inte är jämförbart."}


def _blockers(left: Ledger, right: Ledger) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    notes: list[str] = []
    if left.exam_ids != right.exam_ids:
        reasons.append(f"Alternativen omfattar olika tentamina ({len(left.exam_ids)} mot {len(right.exam_ids)}), så kostnaderna är inte jämförbara.")
    if left.dataset_hash and right.dataset_hash and left.dataset_hash != right.dataset_hash:
        reasons.append("Alternativen bygger på olika dataunderlag, så kostnaderna är inte jämförbara.")
    if left.participants != right.participants:
        reasons.append(f"Efterfrågan skiljer ({left.participants} mot {right.participants} tentander), så en kostnadsskillnad skulle mäta olika behov och inte olika planering.")
    for side, name in ((left, "vänstra"), (right, "högra")):
        if not side.complete:
            shown = "; ".join(f"{item['course'] or item['exam_event_id']}: {item['reason']}" for item in side.unpriced[:3])
            reasons.append(f"Det {name} alternativet ({side.name}) kan inte prissättas fullständigt: {len(side.unpriced)} bokningar saknar sal med pris eller bokning ({shown}"
                           f"{' …' if len(side.unpriced) > 3 else ''}). Ingen totalskillnad redovisas.")
        elif side.cost_kind == COST_KIND_ACTUAL:
            notes.extend(side.assumptions)
            notes.append(f"{side.name} är prissatt med den andra körningens regler och priser: det är en modellberäkning för de historiska bokningarna, inte faktisk kostnad. "
                         "Bemanningen för A är beräknad av bokade platser per sal och är inte observerad bemanning.")
    for side in (left, right):
        priced = price(side.problem, side.sessions)
        # The pool is the solver's own figure and can exceed the peak of a solution that is not proven optimal; everything else must match.
        mismatch = any(priced[name] != side.components[name] for name in COMPONENTS if name != "annual_staff_pool_cost_ore")
        if mismatch and side.cost_kind != COST_KIND_ACTUAL:
            reasons.append(f"Kostnadsunderlaget för {side.name} stämmer inte med körningens redovisade kostnad; ingen förklaring kan göras.")
    return reasons, notes


def _split(left: Ledger, right: Ledger) -> dict[str, Any]:
    """Changed use of resources against changed prices or assumptions, by pricing the right plan with the left rules."""
    if pricing_signature(left.problem) == pricing_signature(right.problem):
        return {"available": True, "usage_ore": right.total - left.total, "assumption_ore": 0, "same_prices": True,
                "note": "Alternativen har samma priser och regler; hela skillnaden är ändrat resursutnyttjande."}
    rooms = {room.room_id for room in left.problem.rooms}
    if any(session.room_id not in rooms for session in right.sessions):
        return {"available": False, "reason": "Det högra alternativet använder salar som saknar pris i det vänstra, så skillnaden kan inte delas upp i utnyttjande och priser."}
    priced = price(left.problem, reprice_staff(left.problem, right.sessions))
    return {"available": True, "usage_ore": priced["comparable_total_cost_ore"] - left.total, "assumption_ore": right.total - priced["comparable_total_cost_ore"],
            "same_prices": False, "_right_at_left": priced,
            "note": "Utnyttjandet är det högra alternativets plan prissatt med det vänstra alternativets priser och regler minus det vänstras kostnad; resten är effekten av andra priser, regler eller antaganden."}


def _items(left: Ledger, right: Ledger, right_at_left: dict[str, int] | None) -> list[dict[str, Any]]:
    rows = []
    for key, label, names in ITEMS:
        row: dict[str, Any] = {"key": key, "label": label, "left_ore": _sum(left.components, names), "right_ore": _sum(right.components, names)}
        row["difference_ore"] = row["right_ore"] - row["left_ore"]
        if right_at_left is not None:
            row["usage_ore"] = _sum(right_at_left, names) - row["left_ore"]
            row["assumption_ore"] = row["right_ore"] - _sum(right_at_left, names)
        elif pricing_signature(left.problem) == pricing_signature(right.problem):
            row["usage_ore"], row["assumption_ore"] = row["difference_ore"], 0
        else:
            row["usage_ore"] = row["assumption_ore"] = None
        if len(names) > 1:
            row["parts"] = [{"key": name, "label": PART_LABELS[name], "left_ore": left.components[name], "right_ore": right.components[name],
                             "difference_ore": right.components[name] - left.components[name]} for name in names]
        row["drivers"] = []
        rows.append(row)
    return rows


def _room_usage(ledger: Ledger, room_id: str) -> dict[str, Any]:
    sessions = [s for s in ledger.sessions if s.room_id == room_id]
    room = next((item for item in ledger.problem.rooms if item.room_id == room_id), None)
    reserved = room_id in {item.room_id for item in ledger.problem.reservations}
    used = bool(sessions) or reserved
    return {"used": used, "reserved_only": reserved and not sessions, "sessions": len(sessions), "booked_minutes": sum(s.end_minute - s.start_minute for s in sessions),
            "fixed_ore": room.annual_fixed_cost_ore if room and used else 0, "external_ore": room.external_session_cost_ore * len(sessions) if room else 0,
            "peak_participants": max((s.participants for s in sessions), default=0)}


def _rooms(left: Ledger, right: Ledger, labels: dict[str, str]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    ids = sorted({r.room_id for ledger in (left, right) for r in ledger.problem.rooms})
    rows, freed, added = [], [], []
    for room_id in ids:
        a, b = _room_usage(left, room_id), _room_usage(right, room_id)
        if not a["used"] and not b["used"]:
            continue
        meta = next((r for ledger in (right, left) for r in ledger.problem.rooms if r.room_id == room_id), None)
        status = "kept" if a["used"] and b["used"] else "avoidable" if a["used"] else "added"
        (freed if status == "avoidable" else added if status == "added" else []).append(room_id)
        rows.append({
            "room_id": room_id, "name": (meta.name if meta and meta.name else labels.get(room_id) or room_id), "kind": meta.kind if meta else "internal",
            "capacity": meta.capacity if meta else None, "cost_origin": meta.cost_origin if meta else None, "cost_object_id": meta.cost_object_id if meta else None,
            "status": status, "left": a, "right": b, "difference_ore": (b["fixed_ore"] + b["external_ore"]) - (a["fixed_ore"] + a["external_ore"]),
            "fixed_difference_ore": b["fixed_ore"] - a["fixed_ore"], "external_difference_ore": b["external_ore"] - a["external_ore"],
            "booked_minutes_difference": b["booked_minutes"] - a["booked_minutes"], "reserved_only": a["reserved_only"] or b["reserved_only"],
        })
    return sorted(rows, key=lambda row: ({"avoidable": 0, "added": 1, "kept": 2}[row["status"]], row["name"])), freed, added


def _session_row(ledger: Ledger, session: PricedSession, labels: dict[str, str]) -> dict[str, Any]:
    room = next((r for r in ledger.problem.rooms if r.room_id == session.room_id), None)
    rows = passes(ledger.problem, [session])
    return {"room_id": session.room_id, "room": (room.name if room and room.name else labels.get(session.room_id) or session.room_id), "date": session.day.isoformat(),
            "start": _clock(session.start_minute), "end": _clock(session.end_minute), "participants": session.participants, "staff": session.staff,
            "paid_minutes": sum(r["paid_minutes"] for r in rows), "external_ore": room.external_session_cost_ore if room else 0,
            "external": bool(room and room.kind == "external"), "exams": list(session.exam_ids)}


def _sessions(left: Ledger, right: Ledger, labels: dict[str, str]) -> dict[str, Any]:
    a, b = {s.key: s for s in left.sessions}, {s.key: s for s in right.sessions}
    removed = [_session_row(left, a[key], labels) for key in sorted(set(a) - set(b), key=lambda k: (k[1], k[2], k[0]))]
    added = [_session_row(right, b[key], labels) for key in sorted(set(b) - set(a), key=lambda k: (k[1], k[2], k[0]))]
    changed = []
    for key in sorted(set(a) & set(b), key=lambda k: (k[1], k[2], k[0])):
        before, after = _session_row(left, a[key], labels), _session_row(right, b[key], labels)
        if (before["participants"], before["staff"], before["end"], before["paid_minutes"], before["exams"]) != (after["participants"], after["staff"], after["end"], after["paid_minutes"], after["exams"]):
            changed.append({"before": before, "after": after, "paid_minutes_difference": after["paid_minutes"] - before["paid_minutes"]})
    external = lambda rows: [row for row in rows if row["external"]]  # noqa: E731
    return {
        "removed": removed[:LIST_LIMIT], "added": added[:LIST_LIMIT], "changed": changed[:LIST_LIMIT], "unchanged": len(set(a) & set(b)) - len(changed),
        "counts": {"left": len(a), "right": len(b), "removed": len(removed), "added": len(added), "changed": len(changed)}, "truncated": max(len(removed), len(added), len(changed)) > LIST_LIMIT,
        "external": {"left": len([s for s in a.values() if _is_external(left, s)]), "right": len([s for s in b.values() if _is_external(right, s)]),
                     "avoided": external(removed)[:LIST_LIMIT], "added": external(added)[:LIST_LIMIT],
                     "avoided_ore": sum(row["external_ore"] for row in external(removed)), "added_ore": sum(row["external_ore"] for row in external(added))},
    }


def _is_external(ledger: Ledger, session: PricedSession) -> bool:
    room = next((r for r in ledger.problem.rooms if r.room_id == session.room_id), None)
    return bool(room and room.kind == "external")


def _staffing(left: Ledger, right: Ledger) -> dict[str, Any]:
    a, b = left.staffing, right.staffing
    days = sorted(set(a["per_day"]) | set(b["per_day"]))
    zero = {"passes": 0, "paid_minutes": 0}
    per_day = [{"date": day, "left_passes": a["per_day"].get(day, zero)["passes"], "right_passes": b["per_day"].get(day, zero)["passes"],
                "left_paid_minutes": a["per_day"].get(day, zero)["paid_minutes"], "right_paid_minutes": b["per_day"].get(day, zero)["paid_minutes"],
                "difference_paid_minutes": b["per_day"].get(day, zero)["paid_minutes"] - a["per_day"].get(day, zero)["paid_minutes"]} for day in days]
    keys = ("passes", "paid_minutes", "worked_minutes", "minimum_top_up_minutes", "travel_minutes", "pool")
    return {
        "unit": "En vaktposition i ett salstillfälle är ett betalt pass: förberedelse, skrivtid och avslut, lägst kortaste betalda pass, plus salens restid.",
        "left": {key: a[key] for key in keys}, "right": {key: b[key] for key in keys}, "difference": {key: b[key] - a[key] for key in keys},
        "per_day": [row for row in per_day if row["difference_paid_minutes"] or row["left_passes"] != row["right_passes"]][:LIST_LIMIT], "days_compared": len(days),
        "origin": {"left": _staff_origin(left), "right": _staff_origin(right)},
        "observed_staffing": {"left": left.observed_staffing, "right": right.observed_staffing},
    }


def _staff_origin(ledger: Ledger) -> str:
    if ledger.cost_kind == COST_KIND_ACTUAL:
        return "model_calculated_from_booked_places"
    return "model_calculated"


def _exams(left: Ledger, right: Ledger, freed: list[str], sessions: dict[str, Any]) -> dict[str, Any]:
    removed = {(s["room_id"], s["date"], s["start"]) for s in sessions["removed"]}
    added = {(s["room_id"], s["date"], s["start"]) for s in sessions["added"]}
    rows, time_changed, room_changed, unchanged = [], 0, 0, 0
    for exam_id in sorted(left.exam_ids & right.exam_ids):
        a, b = left.exams[exam_id], right.exams[exam_id]
        moved = (a["date"], a["start"]) != (b["date"], b["start"])
        rooms_known = bool(a["rooms"] or not a["requires_room"]) and bool(b["rooms"] or not b["requires_room"])
        room = rooms_known and set(a["rooms"]) != set(b["rooms"])
        time_changed += moved
        room_changed += bool(room)
        if not (moved or room):
            unchanged += 1
            continue
        tags = []
        tags += [f"room_freed:{r}" for r in a["rooms"] if r in freed and r not in b["rooms"]]
        if any((r, a["date"], a["start"]) in removed and _external_room(left, r) for r in a["rooms"]):
            tags.append("external_avoided")
        if any((r, b["date"], b["start"]) in added and _external_room(right, r) for r in b["rooms"]):
            tags.append("external_added")
        rows.append({"exam_event_id": exam_id, "course": a.get("course") or b.get("course"), "participants": a.get("participants"),
                     "before": {"date": a["date"], "start": a["start"], "rooms": a["labels"], "room_ids": a["rooms"]},
                     "after": {"date": b["date"], "start": b["start"], "rooms": b["labels"], "room_ids": b["rooms"]},
                     "changes": [name for name, flag in (("date", a["date"] != b["date"]), ("start", a["start"] != b["start"]), ("room", bool(room))) if flag], "tags": tags})
    return {"compared": len(left.exam_ids & right.exam_ids), "unchanged": unchanged, "time_changed": time_changed, "room_changed": room_changed,
            "changed": rows[:LIST_LIMIT], "changed_count": len(rows), "truncated": len(rows) > LIST_LIMIT}


def _external_room(ledger: Ledger, room_id: str) -> bool:
    room = next((r for r in ledger.problem.rooms if r.room_id == room_id), None)
    return bool(room and room.kind == "external")


def _drivers(items, rooms, sessions, staff, exams, labels) -> None:
    """Attach to each cost item the changes that explain it, in words and with the amounts."""
    by_key = {item["key"]: item for item in items}
    moved_from: dict[str, list[str]] = defaultdict(list)
    for row in exams["changed"]:
        for room_id in row["before"]["room_ids"]:
            if room_id not in row["after"]["room_ids"]:
                moved_from[room_id].append(row["course"] or row["exam_event_id"])
    for row in rooms:
        if row["fixed_difference_ore"] == 0:
            continue
        verb = {"avoidable": "används inte längre", "added": "tas i bruk", "kept": "ändrad användning"}[row["status"]]
        who = moved_from.get(row["room_id"], [])
        text = f"{row['name']} {verb}: {'+' if row['fixed_difference_ore'] > 0 else '−'}{_kr(row['fixed_difference_ore'])}" + (f"; tentor som flyttar därifrån: {', '.join(who[:6])}{' …' if len(who) > 6 else ''}" if who else "")
        by_key["rooms"]["drivers"].append({"kind": f"room_{row['status']}", "room_id": row["room_id"], "ore": row["fixed_difference_ore"], "text": text})
    external = sessions["external"]
    if external["avoided"]:
        by_key["external"]["drivers"].append({"kind": "external_avoided", "count": len(external["avoided"]), "ore": -external["avoided_ore"],
                                              "text": f"{len(external['avoided'])} externa bokningar undviks: −{_kr(external['avoided_ore'])}"})
    if external["added"]:
        by_key["external"]["drivers"].append({"kind": "external_added", "count": len(external["added"]), "ore": external["added_ore"],
                                              "text": f"{len(external['added'])} externa bokningar tillkommer: +{_kr(external['added_ore'])}"})
    diff = staff["difference"]
    if diff["paid_minutes"] or diff["passes"]:
        sign = "+" if diff["paid_minutes"] > 0 else "−"
        hours = f"{abs(diff['paid_minutes']) / 60:.1f}".replace(".", ",")
        counts = sessions["counts"]
        by_key["staff"]["drivers"].append({
            "kind": "paid_time", "paid_minutes": diff["paid_minutes"], "passes": diff["passes"],
            "text": f"Betalda personaltimmar {sign}{hours} h ({diff['passes']:+d} betalda pass); {counts['removed']} salstillfällen utgår, {counts['added']} tillkommer, {counts['changed']} ändras."})
    if diff["pool"]:
        by_key["staff"]["drivers"].append({"kind": "pool", "text": f"Vaktpoolen ändras med {diff['pool']:+d} samtidiga vakter."})


def _realization(left: Ledger, right: Ledger, rooms: list[dict[str, Any]], sessions: dict[str, Any]) -> dict[str, Any]:
    snapshot = right.snapshot or left.snapshot
    used_right = {row["room_id"] for row in rooms if row["right"]["used"]}
    items = []
    for row in rooms:
        saving = -(row["fixed_difference_ore"]) if row["status"] == "avoidable" else 0
        if row["kind"] == "external" and row["external_difference_ore"] < 0:
            saving = -row["external_difference_ore"]
        if saving <= 0:
            continue
        items.append({"room_id": row["room_id"], "name": row["name"], "kind": row["kind"], "modelled_saving_ore": saving,
                      "realization": classify_room(snapshot, row["room_id"], row["kind"], used_right)})
    return {"items": items, "summary": summarize(items), "contract_basis": ({"pack_id": snapshot.get("pack_id"), "origin": snapshot.get("origin"), "sha256": snapshot.get("sha256")} if snapshot else None),
            "note": "Lokaler som inte längre används frigör bara sin hyra om avtalsobjektet kan avvecklas. Saknas avtalsuppgifter är besparingen villkorad."}


def _kinds(difference: int | None, realization: dict[str, Any]) -> dict[str, Any]:
    return {
        "historical": {"available": False, "note": "Faktisk kostnad per tentamen, sal eller personalpass finns inte i underlaget (bara en preliminär intern hyra för hela verksamheten)."},
        "model_calculated": {"available": difference is not None, "difference_ore": difference},
        "theoretical_annual_potential": {"available": False, "ore": None, "note": "Kräver en årsomräkning (cost.annualization_factor) och en efterfrågeprofil för den ej simulerade tiden; den finns inte i modellen."},
        "verified_realisable": {"available": realization["summary"]["verified_ore"] > 0, "ore": realization["summary"]["verified_ore"],
                                "note": "Verifierad realiserbar besparing kräver observerade avtalsuppgifter. Simulerade, antagna och modellberäknade uppgifter ger aldrig verifierad besparing."},
    }


def _origins(ledger: Ledger) -> list[str]:
    basis = ledger.problem.resource_basis or {}
    pack = basis.get("pack")
    return list(pack.get("origins") or []) if pack else []


def _basis(left: Ledger, right: Ledger) -> dict[str, Any]:
    def side(ledger: Ledger) -> dict[str, Any]:
        basis = ledger.problem.resource_basis or {}
        pack = basis.get("pack")
        return {"kind": ledger.kind, "name": ledger.name, "cost_kind": ledger.cost_kind, "cost_kind_text": KIND_TEXT[ledger.cost_kind],
                "resource_data": ({"pack_id": pack["pack_id"], "origin": pack["pack_origin"], "origins": pack["origins"]} if pack else None),
                "staffing_origin": _staff_origin(ledger), "priced_by": "own" if ledger.cost_kind != COST_KIND_ACTUAL else "the_other_alternative",
                "reservations": (basis.get("reservations") or {}).get("status"), "optimum": {"gap_ore": ledger.gap_ore, "proven": ledger.proven_optimum}}
    return {"left": side(left), "right": side(right)}


def _quality(left: Ledger, right: Ledger) -> dict[str, Any]:
    simulated = any("simulated" in _origins(ledger) or ((ledger.problem.resource_basis or {}).get("pack") or {}).get("pack_origin") == "simulated"
                    or (ledger.snapshot or {}).get("origin") == "simulated" for ledger in (left, right))
    proxies = sorted({r.room_id for ledger in (left, right) for r in ledger.problem.rooms if r.kind == "internal" and r.cost_origin == "parameter_proxy"
                      and any(s.room_id == r.room_id for s in ledger.sessions)})
    flags = []
    for ledger in (left, right):
        if ledger.assumptions:
            flags.append({"key": "address_only_assumed", "text": "Temporär regel: " + " ".join(ledger.assumptions) + " Kostnaden för A är därför en underkant."})
    if simulated:
        flags.append({"key": "simulated", "text": "Kostnader eller villkor kommer från simulerade testdata. Resultatet visar hur beräkningen fungerar och får inte tolkas som verklig eller verifierad besparing."})
    if proxies:
        flags.append({"key": "proxy_prices", "text": f"{len(proxies)} använda salar saknar kostnad i resursdatan och prissätts per plats enligt en parameter (proxy): {', '.join(proxies[:6])}."})
    if any(((ledger.problem.resource_basis or {}).get("reservations") or {}).get("blocking") for ledger in (left, right)):
        flags.append({"key": "reservation_staff_excluded", "text": "Kvarvarande fasta bokningar påverkar salspärrar och lokalkostnad (en sal med fast bokning räknas som använd), men deras vaktpersonal ingår inte i kostnaden."})
    for ledger in (left, right):
        if ledger.cost_kind == COST_KIND_ACTUAL:
            continue  # A is priced by the rules of the other alternative, which carries the flag
        reservations = (ledger.problem.resource_basis or {}).get("reservations") or {}
        if reservations.get("status") == "ignored_by_parameter":
            flags.append({"key": "reservations_ignored", "text": f"{ledger.name}: fasta bokningar utanför valda tentor ignorerades. Resultatet är explorativt."})
        elif reservations.get("unidentified_bookings"):
            flags.append({"key": "unidentified_bookings", "text": f"{ledger.name}: {reservations['unidentified_bookings']} bokningar utan identifierad sal kunde inte spärra något."})
    if not (left.problem.resource_basis or right.problem.resource_basis):
        flags.append({"key": "legacy_run", "text": "Minst en körning saknar uppgift om resursdata och fasta bokningar (äldre körning)."})
    return {"simulated": simulated, "flags": flags}


def _summary(left: Ledger, right: Ledger, items: list[dict[str, Any]], difference: int) -> str:
    parts = ", ".join(f"{item['label'].lower()} {'+' if item['difference_ore'] > 0 else '−' if item['difference_ore'] < 0 else '±'}{_kr(item['difference_ore'])}" for item in items)
    direction = "lägre" if difference < 0 else "högre" if difference > 0 else "oförändrad"
    return (f"Modellkostnaden är {direction} med {_kr(difference)} för {right.name} jämfört med {left.name} ({_kr(left.total)} mot {_kr(right.total)}): {parts}. "
            "Beloppen är modellberäknade och inte en verifierad besparing.")
