"""B and C – a saved optimisation run, read back from its own files in the same shape as the actual booking (`profile_actual`).

Nothing is recomputed by the engine: the placement, rooms and costs come from the run's `joint_input.json` and
`joint_result.json`, and whether the run counts as a verified solution comes from the independent validation
(`run_summary`). A run without a verified solution has a profile too, but it has no placement, no cost and no
utilisation: it says why it is unavailable and which exams it could not place. A partial placement never appears here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .app_storage import AppStorage
from .joint_summary import read_json, run_summary
from .profile_common import room_usage, utilization
from .run_meta import KIND_USER, read_meta, staleness
from .wishes import RANKS, date_rank

COMPONENT_LABELS = (("annual_room_cost_ore", "Lokaler"), ("annual_staff_pool_cost_ore", "Vaktpool"),
                    ("external_room_session_cost_ore", "Externa salstillfällen"), ("staff_session_cost_ore", "Rörlig bemanning"),
                    ("staff_paid_time_cost_ore", "Betald personaltid"))
DIAGNOSIS_FILE = "joint_diagnosis.json"


def _room_labels(processed_dir: Path) -> dict[str, str]:
    """Room id to the label the bookings use (address and room name as booked), otherwise the register's: the same room reads the same on both sides."""
    path = processed_dir / "room_inventory.csv"
    if not path.is_file():
        return {}
    frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    labels = {}
    for row in frame.to_dict("records"):
        if row["room_id"]:
            address = row.get("observed_addresses") or row.get("reference_address", "")
            name = row.get("observed_room_names") or row.get("reference_room_name", "")
            labels[row["room_id"]] = f"{address} – {name}".strip(" –")
    return labels


def run_name(storage: AppStorage, run_id: str, meta: dict[str, Any] | None) -> str:
    """What the run is called: the name it was saved with, otherwise (older runs) its scenario and start time."""
    if meta and meta.get("name"):
        return str(meta["name"])
    summary_name = run_id.split("Z-", 1)[-1] if "Z-" in run_id else run_id
    return f"{summary_name} ({run_id[:15]})"


def run_profile(storage: AppStorage, run_id: str, current_dataset_hash: str | None = None) -> dict[str, Any]:
    directory = storage.run_directory(run_id)
    problem, result = read_json(directory / "joint_input.json"), read_json(directory / "joint_result.json")
    if problem is None or result is None:
        raise FileNotFoundError("Körningen har inget sparat indata eller resultat.")
    meta = read_meta(directory)
    summary = run_summary(storage, run_id)
    kind = (meta or {}).get("kind", KIND_USER)
    stale = staleness(meta, None, problem.get("dataset_hash"), current_dataset_hash)
    base = {"ref": run_id, "kind": kind, "name": run_name(storage, run_id, meta), "meta": meta, "stale": stale,
            "scope": {"exam_count": len(problem.get("demands", [])), "participants": sum(sum(g["participant_count"] for g in d["participant_groups"]) for d in problem.get("demands", []))},
            "dataset_hash": problem.get("dataset_hash"), "summary": {key: summary.get(key) for key in (
                "solver_outcome", "has_verified_solution", "cost_ore", "lower_bound_ore", "gap_ore", "cost_is_proven_optimum", "changed_exams", "staff_pool_size",
                "wall_time_seconds", "unverified_reason", "cancelled", "verdicts", "planning_basis")}}
    if not summary["has_verified_solution"]:
        return {**base, "available": False, "unavailable_reason": summary.get("unverified_reason") or "Körningen har ingen verifierad lösning.", "exams": [], "metrics": {},
                "wish_distribution": {}, "room_usage": [], "utilization": [], "unplaced": _unplaced(directory, problem, result), "cost": {"kind": "model", "available": False},
                "notes": list(result.get("limitations") or [])}
    return {**base, **_placed(storage, directory, problem, result, summary)}


def _unplaced(directory: Path, problem: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    """Exams a run could not place, with the reason the run recorded. Only reasons that were recorded; none are made up."""
    blocking = str((result.get("verification") or {}).get("blocking_demands") or "")
    ids = [item for item in blocking.split(",") if item]
    reason = next((text for text in (result.get("limitations") or []) if "Blockerande" in text), None)
    diagnosis = read_json(directory / DIAGNOSIS_FILE)
    why = reason or (f"Utredning: {diagnosis['conclusion']}" if diagnosis and diagnosis.get("conclusion") else None)
    if ids:
        return [{"exam_event_id": item.removeprefix("exam-"), "course": None, "reason": reason or "Saknar tillåtet tillfälle."} for item in ids]
    outcome = (result.get("solver") or {}).get("outcome")
    text = {"infeasible": "Ingen fullständig placering finns: de hårda villkoren (salskapacitet, lokaler, datum) går inte ihop för hela efterfrågan.",
            "unknown": "Ingen lösning hittades inom tidsgränsen."}.get(outcome, "Körningen gav ingen verifierad lösning.")
    return [{"exam_event_id": None, "course": None, "reason": why or text, "applies_to": f"alla {len(problem.get('demands', []))} tentor"}]


def _placed(storage: AppStorage, directory: Path, problem: dict[str, Any], result: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    labels = _room_labels(storage.processed_dir)
    rooms = {room["room_id"]: room for room in problem["rooms"]}
    slots = {slot["slot_id"]: slot for slot in problem["slots"]}
    schedule = {row["exam_demand_id"]: row for row in result["schedule"]}
    assigned: dict[str, list[dict[str, Any]]] = {}
    for row in result["assignments"]:
        assigned.setdefault(row["exam_demand_id"], []).append(row)
    exams, items = [], []
    for demand in problem["demands"]:
        row = schedule[demand["exam_demand_id"]]
        slot = slots[row["slot_id"]]
        wish_dates = list(demand.get("wish_dates") or [None, None, None])
        wish_dates += [None] * (3 - len(wish_dates))
        end = slot["start_minute"] + demand["duration_minutes"]
        places = []
        for part in assigned.get(demand["exam_demand_id"], []):
            room = rooms[part["room_id"]]
            label = labels.get(part["room_id"], part["room_id"])
            places.append({"label": label, "room_id": part["room_id"], "capacity": room["capacity"], "booked_places": int(part["participants"]), "identification": "room_matched",
                           "capacity_basis": room.get("capacity_basis", "register"), "in_model_register": room.get("capacity_basis", "register") == "register"})
            items.append({"date": slot["scheduled_date"], "start_min": slot["start_minute"], "end_min": end, "seats": int(part["participants"]), "label": label,
                          "room_id": part["room_id"], "kind": "room_matched", "capacity": room["capacity"], "in_model_register": places[-1]["in_model_register"]})
        event_id = demand["exam_demand_id"].removeprefix("exam-")
        exams.append({
            "exam_event_id": event_id, "course": demand.get("course_code"), "participants": sum(g["participant_count"] for g in demand["participant_groups"]),
            "status": "placed", "date": slot["scheduled_date"], "start": f"{slot['start_minute'] // 60:02d}:{slot['start_minute'] % 60:02d}",
            "end": f"{end // 60 % 24:02d}:{end % 60:02d}", "places": places, "booked_places": sum(p["booked_places"] for p in places), "requires_room": demand.get("requires_room", True),
            "booked": {"date": demand.get("original_date"), "start_minute": demand.get("original_start_minute")}, "movable": demand.get("movable", True),
            "wish": {"dates": wish_dates, "status": demand.get("wish_status", "not_loaded"), "reason": demand.get("wish_reason"),
                     "rank": date_rank(slot["scheduled_date"], tuple(wish_dates)) if any(wish_dates) else "unknown"},  # type: ignore[arg-type]
        })
    distribution = {rank: sum(1 for e in exams if e["wish"]["rank"] == rank) for rank in RANKS}
    distribution["unknown"] = sum(1 for e in exams if e["wish"]["rank"] == "unknown")
    used = {p["room_id"] for e in exams for p in e["places"]}
    outside = {room_id for room_id in used if rooms[room_id].get("capacity_basis", "register") != "register"}
    per_day: dict[str, int] = {}
    for e in exams:
        per_day[e["date"]] = per_day.get(e["date"], 0) + 1
    costs = result.get("costs") or {}
    notes = [f"{len(outside)} salar utanför lokalregistret har kapacitet från största observerade bokning (en underkant, inte en uppmätt kapacitet)."] if outside else []
    return {
        "available": True, "unavailable_reason": None, "exams": exams,
        "metrics": {"rooms_used": len(used), "rooms_in_model_register": len(used - outside), "rooms_outside_model_register": len(outside), "addresses_without_room": 0,
                    "non_physical_places": 0, "staff_pool": result.get("staff_pool_size")},
        "wish_distribution": distribution, "room_usage": room_usage(items), "utilization": utilization(items, per_day), "unplaced": [],
        "cost": {"kind": "model", "available": True, "total_ore": summary.get("cost_ore"), "lower_bound_ore": summary.get("lower_bound_ore"), "gap_ore": summary.get("gap_ore"),
                 "proven_optimum": summary.get("cost_is_proven_optimum"),
                 "components": [{"key": key, "label": label, "ore": costs.get(key)} for key, label in COMPONENT_LABELS if costs.get(key)],
                 "note": "Modellkostnad med scenariots proxypriser och antaganden. Inte faktisk kostnad och inte en verifierad besparing."},
        "notes": notes + list(result.get("limitations") or [])[:6],
    }
