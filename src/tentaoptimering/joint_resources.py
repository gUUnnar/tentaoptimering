"""Put the chosen resource data (`resource_data`) into a joint optimisation problem: named rooms, their costs, external
hire and the staff cost rules. Each figure keeps its origin so that a run can say what it rests on.

The pack decides the *figures*; the run parameters decide the *choices*:

* a room that the pack lists gets its cost, name, cost object and travel minutes from the pack (a registered room whose
  capacity the register knows keeps that capacity). A room the pack does not list keeps the per-seat parameter cost and is
  marked `parameter_proxy`, so the run shows which costs are data and which are placeholders;
* an external room is priced per session as its charging terms say; it has no fixed annual cost;
* staff cost: a parameter that the user changed wins over the pack, otherwise the pack's value is used, otherwise the
  parameter's default. The trace records which of the three decided;
* `rooms.exclude` removes rooms from the model.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from .joint_contract import CandidateSlot, HireWindow, ParameterValue, Reservation, Room
from .money import from_units, to_units
from .joint_reservations import build_reservations
from .resource_data import NamedRoom, ResourceDataError, ResourcePack, pack_basis, pack_directory, resolve_pack, write_snapshot

NO_PACK = "none"
EXTERNAL_BASIS = "resource_data_external"


def pack_id_of(values: dict[str, Any]) -> str:
    return str(values.get("resources.pack") or NO_PACK)


def effective_staff_values(values: dict[str, Any], parameters: tuple[ParameterValue, ...], pack: ResourcePack | None) -> dict[str, Any]:
    """The staff cost values that the engine uses, and where each came from (`parameter`, `resource_data` or `default`)."""
    changed = {item.parameter_id for item in parameters if item.changed_from_default}
    rules = pack.staff if pack else None
    result: dict[str, Any] = {}
    for key, parameter_id, packed in (
        ("paid_minute_cost_kr", "cost.staff_paid_minute_kr", rules.paid_minute_cost_kr if rules else None),
        ("min_paid_minutes", "staffing.min_paid_shift_minutes", rules.min_paid_shift_minutes if rules else None),
        ("annual_cost_kr_per_staff", "cost.staff_annual_kr", rules.pool_annual_cost_kr if rules else None),
    ):
        if parameter_id in changed or packed is None:
            result[key] = {"value": values[parameter_id], "source": "parameter" if parameter_id in changed else "default",
                           "origin": "experiment" if parameter_id in changed else "assumption"}
        else:
            result[key] = {"value": packed, "source": "resource_data", "origin": rules.provenance.origin if rules else "assumption"}
    return result


def apply_resource_pack(
    rooms: tuple[Room, ...], pack: ResourcePack | None, plan_area: str, slots: tuple[CandidateSlot, ...], values: dict[str, Any],
) -> tuple[tuple[Room, ...], dict[str, Any]]:
    """The rooms of the problem with names, costs and external hire from the pack, and the trace of what was used."""
    selection = {str(item) for item in values.get("rooms.selection") or ()}
    excluded = {str(item) for item in values.get("rooms.exclude") or ()}
    warnings: list[str] = []
    trace: list[dict[str, Any]] = []
    result: dict[str, Room] = {room.room_id: room for room in rooms}
    first, last = (min(slot.scheduled_date for slot in slots), max(slot.scheduled_date for slot in slots)) if slots else (None, None)
    if pack is not None:
        if first and last and ((pack.valid_from and first < date.fromisoformat(pack.valid_from)) or (pack.valid_to and last > date.fromisoformat(pack.valid_to))):
            warnings.append(f"Planeringsperioden {first}–{last} ligger delvis utanför resursdatans giltighet ({pack.valid_from or '…'}–{pack.valid_to or '…'}); uppgifterna används ändå.")
        owners = _owners(pack)
        for named in pack.rooms:
            current = result.get(named.room_id)
            if current is None:
                added = _added_room(named, pack, plan_area, slots, selection)
                if added is None:
                    if named.plan_area in (None, plan_area) and named.kind == "internal":
                        warnings.append(f"Resursdatans sal {named.room_id} finns inte i lokalregistret och saknar kapacitet, planeringsområde eller byggnad; den används inte.")
                    continue
                result[named.room_id] = added
            else:
                result[named.room_id] = _priced(current, named, pack, owners, slots)
    unknown_excluded = sorted(excluded - set(result))
    if unknown_excluded:
        raise ValueError(f"Okänd sal i rooms.exclude: {', '.join(unknown_excluded)}. Välj bland salarna i planeringsområdet {plan_area}.")
    chosen = tuple(room for room_id, room in result.items() if room_id not in excluded)
    for room in chosen:
        trace.append({"room_id": room.room_id, "name": room.name, "kind": room.kind, "cost_origin": room.cost_origin, "cost_object_id": room.cost_object_id,
                      "annual_fixed_cost_kr": room.annual_fixed_cost_kr, "session_cost_kr": room.external_session_cost_kr,
                      "travel_paid_minutes": room.travel_paid_minutes})
    proxies = sorted(room.room_id for room in chosen if room.kind == "internal" and room.cost_origin == "parameter_proxy")
    if pack is not None and proxies:
        warnings.append(f"{len(proxies)} salar saknar kostnad i resursdatan och prissätts per plats enligt parametern: {', '.join(proxies)}.")
    return chosen, {"pack": pack_basis(pack) if pack else None, "rooms": trace, "excluded_rooms": sorted(excluded),
                    "warnings": warnings}


def apply_hire_windows(
    pack: ResourcePack | None, rooms: tuple[Room, ...], slots: tuple[CandidateSlot, ...],
) -> tuple[tuple[Room, ...], tuple[HireWindow, ...]]:
    """Whole-facility hires: a room that a hire window names costs nothing per session and is usable only inside its windows.

    A window enters the problem when it overlaps the planning period and one of its rooms is in the model. The window's
    cost is incurred once if any of its rooms is used in the window, whatever the number of rooms or sessions.
    """
    if pack is None or not pack.hire_windows:
        return rooms, ()
    present = {room.room_id for room in rooms}
    first, last = (min(s.scheduled_date for s in slots), max(s.scheduled_date for s in slots)) if slots else (None, None)
    windows = []
    for item in pack.hire_windows:
        start, end = date.fromisoformat(item.start), date.fromisoformat(item.end)
        room_ids = tuple(room_id for room_id in item.room_ids if room_id in present)
        if room_ids and first and last and start <= last and end >= first:
            windows.append(HireWindow(item.window_id, item.name, room_ids, start, end, item.cost_kr, item.provenance.origin, item.provenance.source, item.parts))
    hired = {room_id for item in pack.hire_windows for room_id in item.room_ids}
    result = []
    for room in rooms:
        if room.room_id not in hired:
            result.append(room)
            continue
        inside = {s.slot_id for s in slots if any(room.room_id in w.room_ids and w.start <= s.scheduled_date <= w.end for w in windows)}
        allowed = inside if room.available_slot_ids is None else inside & set(room.available_slot_ids)
        result.append(replace(room, external_session_cost_kr=0, available_slot_ids=tuple(sorted(allowed))))
    return tuple(result), tuple(windows)


def _owners(pack: ResourcePack) -> dict[str, list[NamedRoom]]:
    owners: dict[str, list[NamedRoom]] = {}
    for named in pack.rooms:
        if named.cost_object_id:
            owners.setdefault(named.cost_object_id, []).append(named)
    return owners


def _annual(named: NamedRoom, pack: ResourcePack, owners: dict[str, list[NamedRoom]]) -> tuple[int, str] | None:
    """The room's annual cost: its own figure, otherwise an even share of its cost object (model calculated)."""
    if named.annual_cost_kr is not None:
        return named.annual_cost_kr, named.provenance.origin
    cost_object = pack.cost_object(named.cost_object_id)
    if cost_object is not None and cost_object.annual_cost_kr is not None:
        return from_units(to_units(cost_object.annual_cost_kr) // len(owners[named.cost_object_id])), "model_calculated"
    return None


def _available(named: NamedRoom, current: tuple[str, ...] | None, slots: tuple[CandidateSlot, ...]) -> tuple[str, ...] | None:
    if not (named.available_from or named.available_to):
        return current
    low = date.fromisoformat(named.available_from) if named.available_from else None
    high = date.fromisoformat(named.available_to) if named.available_to else None
    inside = {slot.slot_id for slot in slots if (low is None or slot.scheduled_date >= low) and (high is None or slot.scheduled_date <= high)}
    return tuple(sorted(inside if current is None else inside & set(current)))


def _priced(room: Room, named: NamedRoom, pack: ResourcePack, owners: dict[str, list[NamedRoom]], slots: tuple[CandidateSlot, ...]) -> Room:
    if named.kind == "external":
        return _external(named, room.building_id, room.plan_area, named.capacity or room.capacity, room.digital_capabilities,
                         room.digital_support_basis, room.available_slot_ids, slots)
    annual = _annual(named, pack, owners)
    return replace(
        room, name=named.name, cost_object_id=named.cost_object_id, kind="internal", travel_paid_minutes=named.travel_paid_minutes,
        annual_fixed_cost_kr=annual[0] if annual else room.annual_fixed_cost_kr, cost_origin=annual[1] if annual else room.cost_origin,
        available_slot_ids=_available(named, room.available_slot_ids, slots),
    )


def _external(
    named: NamedRoom, building: str, area: str, capacity: int, capabilities: tuple[str, ...], digital_basis: str,
    available: tuple[str, ...] | None, slots: tuple[CandidateSlot, ...],
) -> Room:
    assert named.charge is not None
    return Room(
        room_id=named.room_id, building_id=building, plan_area=area, capacity=capacity, annual_fixed_cost_kr=0,
        external_session_cost_kr=named.charge.session_cost_kr, digital_capabilities=capabilities,
        available_slot_ids=_available(named, available, slots), digital_support_basis=digital_basis, capacity_basis=EXTERNAL_BASIS,
        name=named.name, cost_object_id=named.cost_object_id, cost_origin=named.provenance.origin, kind="external",
        travel_paid_minutes=named.travel_paid_minutes,
    )


def _added_room(named: NamedRoom, pack: ResourcePack, plan_area: str, slots: tuple[CandidateSlot, ...], selection: set[str]) -> Room | None:
    """A pack room that the register does not have: it joins the model only if the pack says enough to build it."""
    if named.plan_area != plan_area or named.capacity is None or not named.building_id:
        return None
    if selection and named.room_id not in selection:
        return None
    capabilities = ("paper", "e_exam") if named.digital == "e_exam" else ("paper",)
    if named.kind == "external":
        return _external(named, named.building_id, plan_area, named.capacity, capabilities, "not_stated", tuple(slot.slot_id for slot in slots), slots)
    owners = _owners(pack)
    annual = _annual(named, pack, owners)
    if annual is None:
        return None
    return Room(
        room_id=named.room_id, building_id=named.building_id, plan_area=plan_area, capacity=named.capacity, annual_fixed_cost_kr=annual[0],
        digital_capabilities=capabilities, available_slot_ids=_available(named, tuple(slot.slot_id for slot in slots), slots),
        digital_support_basis="not_stated", capacity_basis="resource_data", name=named.name, cost_object_id=named.cost_object_id,
        cost_origin=annual[1], kind="internal", travel_paid_minutes=named.travel_paid_minutes,
    )


def build_resource_layer(
    rooms: tuple[Room, ...], values: dict[str, Any], parameters: tuple[ParameterValue, ...], plan_area: str, slots: tuple[CandidateSlot, ...],
    catalog_path: Path, processed_dir: Path, population_event_ids: set[str],
) -> tuple[tuple[Room, ...], dict[str, Any], tuple[Reservation, ...], dict[str, Any], tuple[HireWindow, ...]]:
    """Rooms with data, the staff values the engine uses, the blocking reservations, the basis record saved in the input
    and the whole-facility hires that apply to the planning period."""
    pack_id = pack_id_of(values)
    pack = resolve_pack(pack_id, pack_directory(catalog_path)) if pack_id != NO_PACK else None
    chosen, trace = apply_resource_pack(rooms, pack, plan_area, slots, values)
    chosen, hire_windows = apply_hire_windows(pack, chosen, slots)
    staff = effective_staff_values(values, parameters, pack)
    reservations, reservation_basis = build_reservations(
        processed_dir, population_event_ids, chosen, slots, str(values.get("reservations.policy", "block_identified")),
        {"no_participant_count": str(values.get("reservations.action_no_count", "keep_fixed")), "outside_selection": str(values.get("reservations.action_outside_selection", "keep_fixed")),
         "not_in_ladok": str(values.get("reservations.action_not_in_ladok", "keep_fixed"))})
    reserved = {item.room_id for item in reservations}
    basis = {**trace, "staff": staff, "reservations": reservation_basis, "reserved_rooms": sorted(reserved),
             "hire_windows": [{"window_id": w.window_id, "name": w.name, "room_ids": list(w.room_ids), "start": w.start.isoformat(),
                               "end": w.end.isoformat(), "cost_kr": w.cost_kr, "origin": w.origin, "parts": [dict(part) for part in w.parts]} for w in hire_windows]}
    return chosen, staff, reservations, basis, hire_windows


SNAPSHOT_FILE = "resource_pack.json"


def save_pack_snapshot(resource_basis: dict[str, Any] | None, catalog_path: Path, run_dir: Path) -> str | None:
    """Freeze the pack that the run used as `resource_pack.json` in the run folder; return the file's SHA-256 (None without a pack).

    The pack is read again and must still have the hash that the problem was built with: a pack changed while the run was
    going is an error, never a silent mix of two versions.
    """
    pack_info = (resource_basis or {}).get("pack")
    if not pack_info:
        return None
    pack = resolve_pack(pack_info["pack_id"], pack_directory(catalog_path))
    if pack.sha256 != pack_info["pack_sha256"]:
        raise ResourceDataError(f"Resursdata ”{pack.pack_id}” ändrades medan körningen pågick; starta körningen igen.")
    return write_snapshot(pack, Path(run_dir) / SNAPSHOT_FILE)
