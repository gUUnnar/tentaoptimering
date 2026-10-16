"""Whether a modelled room saving can become a real saving: the link from a freed room to its lease or contract object.

A room that is no longer used does not by itself release its rent. The rent belongs to a *cost object* (a lease, a
contract, an external hire agreement). This module classifies each room that one alternative uses and the other does not:

* `verified`        the cost object is observed data, avoidable, not shared with a room that is still used, and has a release date.
                    Never reached with simulated, assumed or model-calculated data;
* `possible_unverified`  the terms say avoidable, but they rest on simulated, assumed or calculated figures, so the saving is conditional;
* `blocked_shared`  the object is shared with a room that is still used, so nothing is released until all of its rooms are free;
* `blocked_contract` the terms say the cost cannot be avoided;
* `conditional`     the terms (or the object itself) are missing or unknown: the saving is a model figure only;
* `external_per_booking` an external hire that is charged per booking: an avoided booking is an avoided charge, as far as the terms are known.

The model cost of the room (its allocated annual cost, or the sum of its external charges) is always shown next to the status,
so that a modelled saving is never mistaken for a verified one.
"""

from __future__ import annotations

from typing import Any

VERIFIED_ORIGINS = ("observed",)


def _object_of(snapshot: dict[str, Any] | None, room_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not snapshot:
        return None, None
    room = next((item for item in snapshot.get("rooms", ()) if item["room_id"] == room_id), None)
    if room is None or not room.get("cost_object_id"):
        return room, None
    return room, next((item for item in snapshot.get("cost_objects", ()) if item["cost_object_id"] == room["cost_object_id"]), None)


def classify_room(snapshot: dict[str, Any] | None, room_id: str, kind: str, still_used: set[str]) -> dict[str, Any]:
    """Status and terms for one room that the right-hand alternative no longer uses (or uses less)."""
    room, cost_object = _object_of(snapshot, room_id)
    if cost_object is None:
        return {"status": "conditional", "contract": None,
                "reason": "Rummet saknar kopplat hyres- eller avtalsobjekt i resursdatan; om hyran kan avvecklas är okänt, så besparingen är villkorad."}
    origin = cost_object["provenance"]["origin"]
    contract = {"cost_object_id": cost_object["cost_object_id"], "name": cost_object["name"], "kind": cost_object["kind"],
                "annual_cost_ore": cost_object["annual_cost_ore"], "avoidable": cost_object["avoidable"], "notice_months": cost_object["notice_months"],
                "earliest_release_date": cost_object["earliest_release_date"], "one_off_cost_ore": cost_object["one_off_cost_ore"], "origin": origin}
    siblings = sorted(item["room_id"] for item in snapshot["rooms"] if item.get("cost_object_id") == cost_object["cost_object_id"] and item["room_id"] != room_id)
    shared_in_use = sorted(set(siblings) & still_used)
    if cost_object["kind"] == "external_hire" or kind == "external":
        if cost_object["avoidable"] == "yes" and origin in VERIFIED_ORIGINS:
            return {"status": "external_per_booking", "contract": contract, "reason": "Externhyran debiteras per bokning enligt observerade villkor; en undviken bokning är en undviken debitering."}
        return {"status": "possible_unverified", "contract": contract,
                "reason": f"Externhyran debiteras per bokning, men villkoren är {_origin_text(origin)}; en undviken bokning är därför en modellbesparing som inte är verifierad."}
    if cost_object["avoidable"] == "no":
        return {"status": "blocked_contract", "contract": contract, "reason": "Avtalet kan inte sägas upp enligt resursdatan; hyran finns kvar trots att rummet inte används."}
    if cost_object["avoidable"] == "unknown":
        return {"status": "conditional", "contract": contract, "reason": "Avtalsvillkor (uppsägning, engångskostnad) saknas; besparingen är villkorad."}
    if shared_in_use:
        return {"status": "blocked_shared", "contract": contract, "still_used_rooms": shared_in_use,
                "reason": f"Avtalet omfattar även {', '.join(shared_in_use)} som fortfarande används, så ingen hyra frigörs förrän alla rum i avtalet är lediga."}
    if origin in VERIFIED_ORIGINS and cost_object["earliest_release_date"]:
        return {"status": "verified", "contract": contract, "reason": "Avtalet kan avvecklas enligt observerade villkor och inga andra rum i avtalet används."}
    return {"status": "possible_unverified", "contract": contract,
            "reason": f"Avtalet kan avvecklas enligt resursdatan, men villkoren är {_origin_text(origin)}; besparingen är villkorad och inte verifierad."}


def _origin_text(origin: str) -> str:
    return {"simulated": "simulerade", "assumption": "antagna", "model_calculated": "modellberäknade", "observed": "observerade"}.get(origin, origin)


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Modelled saving of the freed rooms split by what can be said about it. Verified is zero unless an item is verified."""
    def total(*statuses: str) -> int:
        return sum(item["modelled_saving_ore"] for item in items if item["realization"]["status"] in statuses)

    return {
        "modelled_saving_ore": sum(item["modelled_saving_ore"] for item in items),
        "verified_ore": total("verified", "external_per_booking"),
        "conditional_ore": total("possible_unverified", "conditional"),
        "blocked_ore": total("blocked_shared", "blocked_contract"),
        "note": "Modellbesparing är det modellen räknar som sparad kostnad. Verifierad besparing kräver observerade avtalsuppgifter och redovisas aldrig för simulerade, antagna eller modellberäknade uppgifter.",
    }
