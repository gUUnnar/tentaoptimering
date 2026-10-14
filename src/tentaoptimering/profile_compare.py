"""Compare two profiles – A (the actual booking), B or C (saved runs) – side by side, never silently.

`left` is the reference and `right` what is set against it (A against B, A against C, B against C, C against C).
The comparison says what it can compare and what it cannot:

* exams are matched by exam event; only exams present on both sides are compared, and a different set of exams makes cost
  and utilisation figures incomparable (stated, not computed);
* time changes (date or start) are always comparable; room changes only where both sides name rooms of the register, so
  a booking that gave only an address is `not comparable`, not "changed";
* cost is shown by kind: historical (A: none per exam), model cost (runs), and the theoretical difference between two
  model costs – only when both are verified and the cost assumptions are the same. A lower model cost does not by itself
  mean money can be saved: `savings_requirements` lists what would have to change (rooms that could be released, a
  smaller staffing pool), and the contracts and notice periods that decide it are not in the model;
* parameters that differ between two runs are listed; A has none.
"""

from __future__ import annotations

from typing import Any

from .joint_compare import assumption_changes, interpret

CHANGE_LIST_LIMIT = 300
METRIC_ROWS = (
    ("exams_placed", "Placerade tentamina", None), ("rooms_used", "Använda salar", "rooms_used"),
    ("rooms_in_model_register", "…varav i lokalregistret", "rooms_in_model_register"),
    ("rooms_outside_model_register", "…varav utanför lokalregistret", "rooms_outside_model_register"),
    ("addresses_without_room", "Adresser utan angiven sal", "addresses_without_room"), ("staff_pool", "Vaktpool (samtidiga vakter)", "staff_pool"),
)
RANK_LABELS = {"first": "Önskat datum (förstahandsval)", "reserve_1": "Reservdatum 1", "reserve_2": "Reservdatum 2", "other": "Annat datum", "unknown": "Önskemål saknas"}


def _header(profile: dict[str, Any]) -> dict[str, Any]:
    return {key: profile.get(key) for key in ("ref", "kind", "name", "available", "unavailable_reason", "stale", "scope", "meta")}


def _exam_index(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["exam_event_id"]: item for item in profile.get("exams", []) if item.get("status") in ("booked", "placed") and item.get("exam_event_id")}


def _metric(profile: dict[str, Any], key: str, source: str | None) -> Any:
    if not profile.get("available"):
        return None
    if source is None:
        return len(_exam_index(profile))
    return profile["metrics"].get(source)


def _delta(left: Any, right: Any) -> int | None:
    return right - left if isinstance(left, int) and isinstance(right, int) else None


def compare_profiles(left: dict[str, Any], right: dict[str, Any], parameter_changes: list[dict[str, Any]], now_stale_blocks: bool = True) -> dict[str, Any]:
    left_exams, right_exams = _exam_index(left), _exam_index(right)
    reasons: list[str] = []
    for side, profile in (("vänstra", left), ("högra", right)):
        if not profile.get("available"):
            reasons.append(f"Den {side} sidan ({profile.get('name')}) saknar verifierad lösning: {profile.get('unavailable_reason')}")
        elif profile.get("stale") and not profile["stale"]["current"] and now_stale_blocks:
            reasons.append(f"Den {side} sidan ({profile.get('name')}): {profile['stale']['reason']}")
    same_set = set(left_exams) == set(right_exams)
    if left.get("available") and right.get("available") and not same_set:
        reasons.append(f"Sidorna omfattar olika tentamina ({len(left_exams)} mot {len(right_exams)}); bara de {len(set(left_exams) & set(right_exams))} gemensamma jämförs.")
    comparable = not reasons or all("omfattar olika" in item for item in reasons) and bool(set(left_exams) & set(right_exams))
    metrics = [{"key": key, "label": label, "left": _metric(left, key, source), "right": _metric(right, key, source),
                "delta": _delta(_metric(left, key, source), _metric(right, key, source))} for key, label, source in METRIC_ROWS]
    wishes = [{"key": rank, "label": label, "left": left.get("wish_distribution", {}).get(rank), "right": right.get("wish_distribution", {}).get(rank)} for rank, label in RANK_LABELS.items()]
    changes = _changes(left_exams, right_exams) if comparable else None
    return {
        "left": _header(left), "right": _header(right), "comparable": comparable, "reasons": reasons, "metrics": metrics, "wish_distribution": wishes,
        "changes": changes, "unplaced": {"left": left.get("unplaced", []), "right": right.get("unplaced", [])},
        "rooms": _rooms(left, right), "utilization": {"left": left.get("utilization", []), "right": right.get("utilization", [])},
        "cost": _cost(left, right, parameter_changes, comparable and same_set), "parameter_changes": parameter_changes,
        "parameter_note": "Den faktiska bokningen (A) har inga parametrar; den är historik." if "A" in (left.get("kind"), right.get("kind")) else None,
        "notes": [*left.get("notes", []), *right.get("notes", [])],
    }


def _changes(left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """How many shared exams changed time or room from the left to the right side, and which."""
    time_changed = room_changed = same = rooms_not_comparable = 0
    rows = []
    for event_id in sorted(set(left) & set(right)):
        a, b = left[event_id], right[event_id]
        moved = (a["date"], a["start"]) != (b["date"], b["start"])
        a_ids = {p["room_id"] for p in a["places"] if p["room_id"]}
        b_ids = {p["room_id"] for p in b["places"] if p["room_id"]}
        comparable_rooms = bool(a["places"]) and bool(b["places"]) and all(p["room_id"] for p in a["places"]) and all(p["room_id"] for p in b["places"])
        room = comparable_rooms and a_ids != b_ids
        time_changed += moved
        room_changed += bool(room)
        rooms_not_comparable += not comparable_rooms
        same += not moved and not room
        if moved or room:
            rows.append({"exam_event_id": event_id, "course": a.get("course") or b.get("course"), "left": {"date": a["date"], "start": a["start"], "rooms": [p["label"] for p in a["places"]]},
                         "right": {"date": b["date"], "start": b["start"], "rooms": [p["label"] for p in b["places"]]}, "time_changed": moved, "room_changed": bool(room) if comparable_rooms else None})
    return {"compared": len(set(left) & set(right)), "unchanged": same, "time_changed": time_changed, "room_changed": room_changed,
            "rooms_not_comparable": rooms_not_comparable, "list": rows[:CHANGE_LIST_LIMIT], "list_truncated": len(rows) > CHANGE_LIST_LIMIT,
            "note": "Salbyte räknas bara där båda sidor anger salar i lokalregistret. En bokning som bara anger adress eller en sal utanför registret redovisas som inte jämförbar."}


def _room_keys(profile: dict[str, Any]) -> dict[str, str]:
    """Identified rooms of a side: a room with a register id is matched by that id across sides, other named rooms by their label."""
    return {(row["room_id"] or row["label"]): row["label"] for row in profile.get("room_usage", []) if row["kind"] in ("room_matched", "room_named_not_in_register")}


def _rooms(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    a, b = _room_keys(left), _room_keys(right)
    return {"left": left.get("room_usage", []), "right": right.get("room_usage", []),
            "only_left": sorted(a[key] for key in set(a) - set(b)), "only_right": sorted(b[key] for key in set(b) - set(a))}


def _cost(left: dict[str, Any], right: dict[str, Any], changes: list[dict[str, Any]], same_set: bool) -> dict[str, Any]:
    lc, rc = left.get("cost") or {}, right.get("cost") or {}
    block: dict[str, Any] = {"left": lc, "right": rc, "model_difference": None, "interpretation": None, "interpretable": None, "savings_requirements": []}
    both_model = lc.get("kind") == "model" and rc.get("kind") == "model" and lc.get("available") and rc.get("available")
    if not both_model:
        block["interpretation"] = ("Modellkostnad finns bara för körningar. Den faktiska bokningen (A) har ingen kostnad per tentamen i underlaget, så en kostnadsskillnad mot A "
                                   "kan inte beräknas. Jämför salar, bemanning och placering nedan. Modellkostnaden för samma tentor med historiska datum låsta kan räknas fram under Resultat, men den är en modellberäkning och inte den faktiska bokningen.") if "A" in (left.get("kind"), right.get("kind")) else "Minst en körning saknar verifierad kostnad."
        block["savings_requirements"] = _savings_requirements(left, right)
        return block
    assumptions = assumption_changes(changes)
    if not same_set:
        block["interpretation"] = "Körningarna omfattar olika tentamina, så kostnaderna är inte jämförbara."
        return block
    if assumptions["cost"] or assumptions["demand"]:
        block["interpretation"] = ("Kostnads-, bemannings- eller efterfrågeantagandena skiljer sig mellan körningarna. Då mäter en kostnadsskillnad antagandena och inte en effektivare placering, "
                                   "så ingen kostnadsskillnad redovisas.")
        block["interpretable"] = False
        block["savings_requirements"] = _savings_requirements(left, right)
        return block
    delta = rc["total_ore"] - lc["total_ore"]
    gaps = [item.get("gap_ore") for item in (lc, rc)]
    uncertainty = max(gaps) if all(isinstance(gap, int) for gap in gaps) else None
    block["model_difference"] = {"ore": delta, "uncertainty_ore": uncertainty, "label": "Teoretisk skillnad i modellkostnad (höger minus vänster), inte en verifierad besparing"}
    block["interpretable"], block["interpretation"] = interpret(delta, uncertainty)
    block["savings_requirements"] = _savings_requirements(left, right)
    return block


def _savings_requirements(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    """What would have to change in practice for a lower model cost to become lower real cost. Only what the two sides show."""
    out = []
    a, b = _room_keys(left), _room_keys(right)
    only_left = sorted(a[key] for key in set(a) - set(b))
    if only_left and right.get("available"):
        out.append(f"Salar som används på vänster sida men inte på höger: {', '.join(only_left)}. Kostnaden minskar bara om de faktiskt kan sägas upp, hyras ut eller avvecklas; hyresavtal och uppsägningstider ingår inte i modellen.")
    pools = (left.get("metrics") or {}).get("staff_pool"), (right.get("metrics") or {}).get("staff_pool")
    if all(isinstance(item, int) for item in pools) and pools[1] < pools[0]:
        out.append(f"Vaktpoolen är {pools[0] - pools[1]} samtidiga vakter mindre. Det ger lägre kostnad bara om anställningar eller timtimmar verkligen kan minskas.")
    if not out:
        out.append("Jämförelsen visar ingen sal som kan frigöras eller någon mindre vaktpool; en effektivare placering ger då ingen kostnadsminskning i sig.")
    return out
