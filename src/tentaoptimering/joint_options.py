"""The choices that a scenario offers in the interface: which rooms exist and which exam types occur.

`GET /api/joint-runs/options` answers two questions the parameter editor cannot answer on its own:

* which rooms the engine would consider for the scenario's plan area (the values `rooms.selection` may name);
* which exam types occur among the scenario's exams (what `flex.movable_types` is matched against).

The room list is the same one the engine builds its rooms from (`eligible_rooms`), so the interface cannot offer a
room the engine ignores. Nothing here changes a run: it only reads the prepared data.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

from .joint_selection import select_ready_demands

DEMANDS_FILE, ROOMS_FILE = "optimization_demands.csv", "optimization_rooms.csv"
_TYPE_SEPARATORS = re.compile(r"\s*[|;]\s*")
_NO_DIGITAL_PREFIXES = ("no_", "none", "not_supported")


def building_id(address: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", address.lower()).strip("-")


def eligible_rooms(rooms_frame: pd.DataFrame, plan_area: str) -> pd.DataFrame:
    """The rooms that the engine may consider in a plan area, before any `rooms.selection` is applied."""
    return rooms_frame[
        rooms_frame["eligible_for_exploratory_capacity_poc"].astype(bool) & (rooms_frame["reference_city"] == plan_area)
    ].copy()


def select_rooms(rooms_frame: pd.DataFrame, plan_area: str, selection: object) -> pd.DataFrame:
    """The eligible rooms limited to `selection` (an empty selection means all). An unknown room id is an error."""
    rows = eligible_rooms(rooms_frame, plan_area)
    wanted = [str(value) for value in selection]  # type: ignore[attr-defined]
    if not wanted:
        return rows
    unknown = unknown_rooms(wanted, rows)
    if unknown:
        ending = " Urvalet lämnar inga salar att planera med." if len(unknown) == len(set(wanted)) else ""
        raise ValueError(f"Okänd sal: {', '.join(unknown)}. Välj bland salarna i planeringsområdet {plan_area}.{ending}")
    return rows[rows["room_id"].isin(set(wanted))]


def unknown_rooms(wanted: list[str], eligible: pd.DataFrame) -> list[str]:
    """Distinct ids in `wanted` that are not among the eligible rooms, in the order given."""
    known = set(eligible["room_id"].astype(str))
    return list(dict.fromkeys(value for value in wanted if value not in known))


def digital_level(status: str) -> str:
    """How much of a room supports digital exams: `all`, `partial`, `none` or `unknown`."""
    if status.startswith("all_places"):
        return "all"
    if status.startswith("supports_e_exam"):
        return "partial"
    return "none" if status.startswith(_NO_DIGITAL_PREFIXES) else "unknown"


def room_selection_errors(
    processed_dir: Path, content: dict[str, Any], selection: object
) -> list[dict[str, str]]:
    """`{id, message}` for room ids that the scenario's plan area does not have; empty when the data is not there."""
    frame = _read(processed_dir, ROOMS_FILE)
    if frame is None or not isinstance(selection, list):
        return []
    try:
        select_rooms(frame, str(content["subset"].get("plan_area", "")), selection)
    except ValueError as error:
        return [{"id": "rooms.selection", "message": str(error)}]
    return []


def options_payload(processed_dir: Path, scenario_id: str, content: dict[str, Any]) -> dict[str, Any]:
    """The payload of `GET /api/joint-runs/options`; empty lists (and `data_available` false) without prepared data."""
    subset = content["subset"]
    plan_area = str(subset.get("plan_area", ""))
    rooms_frame, demands = _read(processed_dir, ROOMS_FILE), _read(processed_dir, DEMANDS_FILE)
    available = rooms_frame is not None and demands is not None
    rooms = _room_rows(rooms_frame, plan_area) if available else []
    return {
        "scenario_id": scenario_id, "data_available": available,
        "rooms": rooms + (_pack_room_rows(str(content.get("parameters", {}).get("resources.pack", "none")), plan_area, {row["room_id"] for row in rooms}) if available else []),
        "exam_types": _type_rows(demands, subset) if available else [],
        "plan_area": plan_area,
    }


def _read(processed_dir: Path, name: str) -> pd.DataFrame | None:
    path = processed_dir / name
    if not path.is_file():
        return None
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except (OSError, ValueError):
        return None


def _room_rows(rooms_frame: pd.DataFrame, plan_area: str) -> list[dict[str, Any]]:
    rows = []
    for row in eligible_rooms(rooms_frame, plan_area).itertuples(index=False):
        address, capacity = str(row.reference_address), int(row.capacity_seats)
        building = building_id(address)
        rows.append({
            "room_id": str(row.room_id), "label": f"{address} – {row.room_id} ({capacity} platser)",
            "building_id": building, "address": address, "capacity": capacity,
            "digital": digital_level(str(row.digital_capability_status)),
        })
    return sorted(rows, key=lambda item: (item["building_id"], -item["capacity"], item["room_id"]))


def _pack_room_rows(pack_id: str, plan_area: str, known: set[str]) -> list[dict[str, Any]]:
    """Rooms that the scenario's resource pack adds to the register (external halls): they can be chosen or left out like any room."""
    if pack_id in ("", "none"):
        return []
    from .app_paths import bundled_joint_catalog_path
    from .resource_data import ResourceDataError, pack_directory, resolve_pack

    try:
        pack = resolve_pack(pack_id, pack_directory(bundled_joint_catalog_path()))
    except (ResourceDataError, OSError):
        return []
    rows = [{"room_id": room.room_id, "label": f"{room.name} – extern ({room.capacity} platser)", "building_id": str(room.building_id), "address": room.name,
             "capacity": int(room.capacity or 0), "digital": "all" if room.digital == "e_exam" else "none"}
            for room in pack.rooms if room.room_id not in known and room.plan_area == plan_area and room.capacity and room.building_id]
    return sorted(rows, key=lambda item: (item["building_id"], -item["capacity"], item["room_id"]))


def _type_rows(demands: pd.DataFrame, subset: dict[str, Any]) -> list[dict[str, Any]]:
    """Observed exam types of the scenario's exams, with the number of exams (events) that have each type."""
    try:
        ready = select_ready_demands(demands, subset)
    except ValueError:
        return []
    events: dict[str, set[str]] = {}
    spelled: dict[str, dict[str, int]] = {}
    for event_id, text in zip(ready["exam_event_id"].astype(str), ready["observed_exam_types"].fillna("").astype(str)):
        for part in _TYPE_SEPARATORS.split(text):
            part = part.strip()
            if part:
                events.setdefault(part.lower(), set()).add(event_id)
                spelled.setdefault(part.lower(), {})[part] = spelled.get(part.lower(), {}).get(part, 0) + 1
    rows = [{"value": value, "label": max(spelled[value], key=lambda form: (spelled[value][form], form)), "count": len(ids)}
            for value, ids in events.items()]
    return sorted(rows, key=lambda item: (-item["count"], item["value"]))
