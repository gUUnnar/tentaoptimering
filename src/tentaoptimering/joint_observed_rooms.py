"""Rooms that the bookings used but the room register gives no capacity: an explicit, switchable assumption.

The register (`optimization_rooms.csv`) holds the published rooms with a capacity. The bookings also name rooms that are
identified but have no published capacity (for example the Fyrishov halls). Without them the bookings of a peak day do
not fit the register at all, so any plan from the business's wishes is infeasible for a reason that is a data gap, not a
planning problem.

`rooms.include_observed_unregistered` adds such rooms to a run. Their capacity is the largest number of places ever booked
in them. That is a *lower bound* of the real capacity, never a measured one, and the room is marked with this basis
(`Room.capacity_basis`) in the saved input. A room that is only an address (no room name), a non-physical place such as
"Hemma", and a room that was never booked are not added: none of them is an identified room with an observed use.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .joint_contract import Room
from .joint_options import building_id

OBSERVED_BASIS = "observed_booked_places_max_lower_bound"


def observed_unregistered_rooms(inventory: pd.DataFrame | None, plan_area: str, slot_ids: tuple[str, ...], registered_ids: set[str]) -> tuple[Room, ...]:
    """Rooms of the inventory with no capacity but with booked use, in the plan area, not already in the register set."""
    if inventory is None or inventory.empty:
        return ()
    rooms = []
    for row in inventory.itertuples(index=False):
        room_id, address = row.room_id, row.observed_addresses
        usable = (
            isinstance(room_id, str) and room_id and not room_id.startswith("derived-") and room_id not in registered_ids
            and isinstance(address, str) and pd.isna(row.capacity_seats)
            and (isinstance(row.observed_cities, str) and plan_area in row.observed_cities.split(" | "))
            and not pd.isna(row.observed_booked_places_max) and float(row.observed_booked_places_max) >= 1
            and not pd.isna(row.observed_placement_count) and float(row.observed_placement_count) >= 1
        )
        if not usable:
            continue
        rooms.append(Room(
            room_id=str(room_id), building_id=building_id(str(address)), plan_area=plan_area, capacity=int(float(row.observed_booked_places_max)),
            annual_fixed_cost_ore=0, external_session_cost_ore=0, digital_capabilities=("paper",),
            available_slot_ids=slot_ids, digital_support_basis="unknown", capacity_basis=OBSERVED_BASIS,
        ))
    return tuple(sorted(rooms, key=lambda item: item.room_id))


def with_price(room: Room, price_per_seat_ore: int) -> Room:
    """Same price rule as for registered rooms: the annual cost per seat times the capacity."""
    from dataclasses import replace

    return replace(room, annual_fixed_cost_ore=room.capacity * price_per_seat_ore)


def describe(rooms: tuple[Room, ...]) -> list[dict[str, Any]]:
    return [{"room_id": item.room_id, "capacity": item.capacity, "capacity_basis": item.capacity_basis} for item in rooms]
