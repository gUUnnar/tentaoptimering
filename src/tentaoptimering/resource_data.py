"""Resource data: named rooms, lease and contract objects, external hire and staff cost rules, each with its origin.

One contract carries both real figures and clearly marked simulated ones. A pack is a TOML file in
`config/resource_data/`; replacing the simulated pack with a real one means adding another file with the same
schema and selecting it by the parameter `resources.pack`. No code changes.

Every record says where it comes from (`origin`) and when it holds (`valid_from`, `valid_to`):

* `observed`: read from a real source (a lease, an invoice, a payroll extract);
* `model_calculated`: derived by a stated rule from observed data;
* `simulated`: an invented but realistic test value. It is never presented as an observation;
* `assumption`: a qualified assumption that is declared and replaceable.

A room that stops being used does not by itself release its rent. The room points to a *cost object* (a lease or
contract) which says whether the cost is avoidable, the notice period, the earliest release date and one-off costs.
Where these are `unknown`, a saving is only conditional (see `cost_realization`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import hashlib
import json
from pathlib import Path
import tomllib
from typing import Any

SCHEMA_VERSION = "resource-data-v1"
ORIGINS = ("observed", "model_calculated", "simulated", "assumption")
AVOIDABLE = ("yes", "no", "unknown")
COST_OBJECT_KINDS = ("internal_rent", "external_lease", "owned", "external_hire")
ROOM_KINDS = ("internal", "external")
CHARGE_BASES = ("per_session", "per_hour")
PACK_DIR_NAME = "resource_data"


class ResourceDataError(ValueError):
    """The resource data is malformed or inconsistent; the message is Swedish and names the record."""


@dataclass(frozen=True)
class Provenance:
    origin: str
    source: str = ""
    valid_from: str | None = None
    valid_to: str | None = None
    note: str = ""


@dataclass(frozen=True)
class CostObject:
    cost_object_id: str
    name: str
    kind: str
    annual_cost_ore: int | None
    avoidable: str
    notice_months: int | None
    earliest_release_date: str | None
    one_off_cost_ore: int | None
    provenance: Provenance


@dataclass(frozen=True)
class ExternalCharge:
    """How an external room is charged. `session_cost_ore` is derived: the price of one session as the engine prices it."""

    basis: str
    price_ore: int
    min_billed_minutes: int
    assumed_billed_minutes: int
    terms: str

    @property
    def session_cost_ore(self) -> int:
        if self.basis == "per_session":
            return self.price_ore
        billed = max(self.min_billed_minutes, self.assumed_billed_minutes)
        return (self.price_ore * billed + 30) // 60  # whole öre, rounded to nearest


@dataclass(frozen=True)
class NamedRoom:
    room_id: str
    name: str
    kind: str
    plan_area: str | None
    building_id: str | None
    capacity: int | None
    digital: str | None
    annual_cost_ore: int | None
    cost_object_id: str | None
    travel_paid_minutes: int
    available_from: str | None
    available_to: str | None
    charge: ExternalCharge | None
    provenance: Provenance


@dataclass(frozen=True)
class StaffRules:
    """Cost and pay rules for the paid staff time. `None` means the pack does not say; the parameters then decide."""

    paid_minute_cost_ore: int | None
    min_paid_shift_minutes: int | None
    pool_annual_cost_ore: int | None
    rules_basis: str
    provenance: Provenance


@dataclass(frozen=True)
class ActualStaffing:
    """Staffing that was actually used, when data exists. Origin `observed` only for real records."""

    date: str
    room_id: str
    staff_count: int
    paid_minutes: int | None
    provenance: Provenance


@dataclass(frozen=True)
class ResourcePack:
    pack_id: str
    name: str
    origin: str
    description: str
    replaced_by: str
    valid_from: str | None
    valid_to: str | None
    cost_objects: tuple[CostObject, ...] = ()
    rooms: tuple[NamedRoom, ...] = ()
    staff: StaffRules | None = None
    actual_staffing: tuple[ActualStaffing, ...] = ()
    sha256: str = ""
    warnings: tuple[str, ...] = field(default=())

    def room(self, room_id: str) -> NamedRoom | None:
        return next((item for item in self.rooms if item.room_id == room_id), None)

    def cost_object(self, cost_object_id: str | None) -> CostObject | None:
        return next((item for item in self.cost_objects if item.cost_object_id == cost_object_id), None) if cost_object_id else None

    def snapshot(self) -> dict[str, Any]:
        """The pack as JSON, saved with every run that used it."""
        payload = asdict(self)
        payload["rooms"] = [{**asdict(item), "session_cost_ore": item.charge.session_cost_ore if item.charge else None} for item in self.rooms]
        return payload


def pack_directory(catalog_path: Path) -> Path:
    """The pack folder that belongs to a parameter catalog (both live under `config/`)."""
    return Path(catalog_path).resolve().parent / PACK_DIR_NAME


def list_packs(directory: Path) -> list[dict[str, str]]:
    """The packs in a folder with their id, name and origin, for choosing in the interface."""
    found = []
    for path in sorted(Path(directory).glob("*.toml")) if Path(directory).is_dir() else []:
        try:
            pack = load_pack(path)
        except (ResourceDataError, OSError, tomllib.TOMLDecodeError):
            continue
        found.append({"id": pack.pack_id, "name": pack.name, "origin": pack.origin, "file": path.name})
    return found


def resolve_pack(pack_id: str, directory: Path) -> ResourcePack:
    """Load the pack with this id. A missing pack is an error: the run never silently continues without it."""
    path = Path(directory) / f"{pack_id}.toml"
    if not path.is_file():
        raise ResourceDataError(f"Resursdata ”{pack_id}” finns inte i {directory}.")
    pack = load_pack(path)
    if pack.pack_id != pack_id:
        raise ResourceDataError(f"Filen {path.name} innehåller resursdata ”{pack.pack_id}”, inte ”{pack_id}”.")
    return pack


def load_pack(path: Path) -> ResourcePack:
    raw = Path(path).read_bytes()
    document = tomllib.loads(raw.decode("utf-8"))
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ResourceDataError(f"{Path(path).name}: okänd schemaversion {document.get('schema_version')!r}.")
    header = document.get("pack") or {}
    pack_id = _text(header, "id", "pack")
    origin = _origin(header.get("origin"), f"pack {pack_id}")
    cost_objects = tuple(_cost_object(item) for item in document.get("cost_object", ()))
    rooms = tuple(_room(item, origin) for item in document.get("room", ()))
    pack = ResourcePack(
        pack_id=pack_id, name=_text(header, "name", "pack"), origin=origin, description=str(header.get("description", "")),
        replaced_by=str(header.get("replaced_by", "")), valid_from=_day(header.get("valid_from"), "pack"), valid_to=_day(header.get("valid_to"), "pack"),
        cost_objects=cost_objects, rooms=rooms, staff=_staff(document.get("staff"), origin),
        actual_staffing=tuple(_actual(item, origin) for item in document.get("actual_staffing", ())),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
    _check(pack)
    return pack


def pack_basis(pack: ResourcePack) -> dict[str, Any]:
    """The short provenance record stored in the problem: which pack, its hash and what kind of figures it holds."""
    origins = sorted({item.provenance.origin for item in pack.rooms} | {item.provenance.origin for item in pack.cost_objects}
                     | ({pack.staff.provenance.origin} if pack.staff else set()))
    return {"pack_id": pack.pack_id, "pack_sha256": pack.sha256, "pack_origin": pack.origin, "origins": origins,
            "rooms": len(pack.rooms), "cost_objects": len(pack.cost_objects), "valid_from": pack.valid_from, "valid_to": pack.valid_to}


def write_snapshot(pack: ResourcePack, path: Path) -> str:
    """Save the pack as the run's own frozen copy and return the file's SHA-256 (recorded in the manifest)."""
    data = json.dumps(pack.snapshot(), ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    Path(path).write_bytes(data)  # bytes, so that the recorded hash is the hash of the file on every platform
    return hashlib.sha256(data).hexdigest()


def _text(item: dict[str, Any], key: str, where: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ResourceDataError(f"{where}: fältet ”{key}” saknas.")
    return value.strip()


def _origin(value: Any, where: str) -> str:
    if value not in ORIGINS:
        raise ResourceDataError(f"{where}: ursprung måste vara en av {', '.join(ORIGINS)} (fick {value!r}).")
    return str(value)


def _day(value: Any, where: str) -> str | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as error:
        raise ResourceDataError(f"{where}: ogiltigt datum {value!r}.") from error


def _money(value: Any, where: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ResourceDataError(f"{where}: belopp i hela öre (icke-negativt heltal) förväntades, fick {value!r}.")
    return int(value)


def _provenance(item: dict[str, Any], where: str, fallback: str) -> Provenance:
    return Provenance(_origin(item.get("origin", fallback), where), str(item.get("source", "")), _day(item.get("valid_from"), where),
                      _day(item.get("valid_to"), where), str(item.get("note", "")))


def _cost_object(item: dict[str, Any]) -> CostObject:
    key = _text(item, "id", "cost_object")
    where = f"cost_object {key}"
    kind = item.get("kind")
    avoidable = str(item.get("avoidable", "unknown"))
    if kind not in COST_OBJECT_KINDS or avoidable not in AVOIDABLE:
        raise ResourceDataError(f"{where}: kind måste vara en av {COST_OBJECT_KINDS} och avoidable en av {AVOIDABLE}.")
    notice = item.get("notice_months")
    if notice is not None and (isinstance(notice, bool) or not isinstance(notice, int) or notice < 0):
        raise ResourceDataError(f"{where}: notice_months måste vara ett icke-negativt heltal.")
    return CostObject(key, _text(item, "name", where), str(kind), _money(item.get("annual_cost_ore"), where), avoidable, notice,
                      _day(item.get("earliest_release_date"), where), _money(item.get("one_off_cost_ore"), where),
                      _provenance(item, where, "assumption"))


def _room(item: dict[str, Any], pack_origin: str) -> NamedRoom:
    key = _text(item, "id", "room")
    where = f"room {key}"
    kind = str(item.get("kind", "internal"))
    if kind not in ROOM_KINDS:
        raise ResourceDataError(f"{where}: kind måste vara internal eller external.")
    charge = None
    if "charge" in item:
        raw = item["charge"]
        basis = str(raw.get("basis", ""))
        if basis not in CHARGE_BASES:
            raise ResourceDataError(f"{where}: charge.basis måste vara en av {CHARGE_BASES}.")
        charge = ExternalCharge(basis, _money(raw.get("price_ore"), where) or 0, int(raw.get("min_billed_minutes", 0)),
                                int(raw.get("assumed_billed_minutes", 0)), str(raw.get("terms", "")))
    capacity = item.get("capacity")
    if capacity is not None and (isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0):
        raise ResourceDataError(f"{where}: capacity måste vara ett positivt heltal.")
    travel = int(item.get("travel_paid_minutes", 0))
    if travel < 0:
        raise ResourceDataError(f"{where}: travel_paid_minutes måste vara icke-negativt.")
    return NamedRoom(
        key, _text(item, "name", where), kind, item.get("plan_area"), item.get("building_id"), capacity, item.get("digital"),
        _money(item.get("annual_cost_ore"), where), item.get("cost_object_id"), travel, _day(item.get("available_from"), where),
        _day(item.get("available_to"), where), charge, _provenance(item, where, pack_origin),
    )


def _staff(item: dict[str, Any] | None, pack_origin: str) -> StaffRules | None:
    if item is None:
        return None
    where = "staff"
    minimum = item.get("min_paid_shift_minutes")
    return StaffRules(_money(item.get("paid_minute_cost_ore"), where), None if minimum is None else int(minimum),
                      _money(item.get("pool_annual_cost_ore"), where), str(item.get("rules_basis", "")), _provenance(item, where, pack_origin))


def _actual(item: dict[str, Any], pack_origin: str) -> ActualStaffing:
    where = "actual_staffing"
    count = item.get("staff_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ResourceDataError(f"{where}: staff_count måste vara ett icke-negativt heltal.")
    paid = item.get("paid_minutes")
    return ActualStaffing(_day(item.get("date"), where) or "", _text(item, "room_id", where), count, None if paid is None else int(paid),
                          _provenance(item, where, pack_origin))


def _check(pack: ResourcePack) -> None:
    ids = [item.room_id for item in pack.rooms]
    if len(ids) != len(set(ids)):
        raise ResourceDataError("Resursdata har dubblerade sal-id:n.")
    object_ids = [item.cost_object_id for item in pack.cost_objects]
    if len(object_ids) != len(set(object_ids)):
        raise ResourceDataError("Resursdata har dubblerade avtalsobjekt.")
    for room in pack.rooms:
        if room.cost_object_id and room.cost_object_id not in object_ids:
            raise ResourceDataError(f"Salen {room.room_id} hänvisar till okänt avtalsobjekt {room.cost_object_id}.")
        if room.kind == "external" and (room.charge is None or room.capacity is None or not room.plan_area or not room.building_id):
            raise ResourceDataError(f"Den externa salen {room.room_id} måste ange charge, capacity, plan_area och building_id.")
        if room.kind == "internal" and room.charge is not None:
            raise ResourceDataError(f"Den interna salen {room.room_id} kan inte ha en extern debitering.")
        if room.kind == "internal" and room.cost_object_id is None and room.annual_cost_ore is None:
            raise ResourceDataError(f"Den interna salen {room.room_id} måste ange annual_cost_ore eller cost_object_id.")
    known = set(ids)
    for row in pack.actual_staffing:
        if row.room_id not in known:
            raise ResourceDataError(f"Faktisk bemanning hänvisar till okänd sal {row.room_id}.")
