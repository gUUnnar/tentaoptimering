"""The configuration of the booking data quality layer (`config/booking_data_quality.toml`), read and validated.

Everything that interprets the data is a *rule* with an `id`, a `verified` flag and a `source`. A rule that the data owner has not
verified never classifies anything (the classifier only notes that a row resembles it). New verified facts, or other column
names in a new extract, are added in the file; no code changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import tomllib
from typing import Any

from ..app_paths import application_root

SCHEMA = "booking-data-quality-v1"
STATUS_CLASSES = ("cancelled", "active")
DEFAULT_COLUMNS = {"placement_id": "placement_id", "exam_order_id": "exam_order_id", "address": "address", "room": "room", "location_key": "location_key",
                   "status": "status", "date": "scheduled_date", "time": "scheduled_time", "places": "booked_places"}


def default_config_path() -> Path:
    return application_root() / "config" / "booking_data_quality.toml"


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    verified: bool
    source: str
    match: dict[str, str] = field(default_factory=dict)
    value_class: str | None = None  # status rules only

    def matches(self, values: dict[str, str]) -> bool:
        """True when every field the rule names equals the row's (compared as stripped text); a rule without fields never matches."""
        return bool(self.match) and all(values.get(key, "").strip() == wanted for key, wanted in self.match.items())


@dataclass(frozen=True)
class QualityConfig:
    version: str
    columns: dict[str, str]
    register: dict[str, str]
    linkage: dict[str, Any]
    coverage: dict[str, str]
    rules: tuple[Rule, ...]
    digest: str
    path: str

    def rules_of(self, kind: str) -> tuple[Rule, ...]:
        return tuple(rule for rule in self.rules if rule.kind == kind)


def _need(table: dict[str, Any], key: str, where: str) -> Any:
    if key not in table:
        raise ValueError(f"Konfigurationen för bokningsdata saknar {key} i {where}.")
    return table[key]


def _rules(content: dict[str, Any], table: str, kind: str, fields: tuple[str, ...]) -> list[Rule]:
    rules = []
    for index, raw in enumerate(content.get(table, []), start=1):
        where = f"[[{table}]] nr {index}"
        rule_id = str(_need(raw, "id", where))
        if not isinstance(raw.get("verified"), bool):
            raise ValueError(f"Regel {rule_id}: verified måste vara true eller false.")
        source = str(raw.get("source", "")).strip()
        if raw["verified"] and not source:
            raise ValueError(f"Regel {rule_id} är verifierad men anger ingen källa (source). Ange vem eller vad som bekräftat den.")
        match = {name: str(raw[name]).strip() for name in fields if name in raw}
        value_class = None
        if kind == "status":
            value_class = str(_need(raw, "class", where))
            if value_class not in STATUS_CLASSES:
                raise ValueError(f"Regel {rule_id}: okänd statusklass {value_class!r}. Tillåtet: {', '.join(STATUS_CLASSES)}.")
            match = {"status": str(_need(raw, "value", where)).strip()}
        elif not match:
            raise ValueError(f"Regel {rule_id} anger inget fält att matcha ({', '.join(fields)}) och skulle aldrig gälla.")
        unknown = set(raw) - {"id", "verified", "source", "note", "class", "value", *fields}
        if unknown:
            raise ValueError(f"Regel {rule_id} har okända fält: {', '.join(sorted(unknown))}.")
        rules.append(Rule(rule_id, kind, raw["verified"], source, match, value_class))
    return rules


def load_config(path: Path | None = None) -> QualityConfig:
    """Read and validate the configuration; any inconsistency is a Swedish `ValueError` naming the rule or key."""
    path = path or default_config_path()
    text = path.read_text(encoding="utf-8")
    content = tomllib.loads(text)
    if content.get("schema_version") != SCHEMA:
        raise ValueError(f"Konfigurationen för bokningsdata har schemat {content.get('schema_version')!r}; förväntat {SCHEMA!r}.")
    columns = {**DEFAULT_COLUMNS, **content.get("columns", {})}
    unknown_columns = set(columns) - set(DEFAULT_COLUMNS)
    if unknown_columns:
        raise ValueError(f"Okända kolumnnycklar i [columns]: {', '.join(sorted(unknown_columns))}.")
    rules = (_rules(content, "status_rule", "status", ("status",)) + _rules(content, "non_physical_rule", "non_physical", ("address", "room"))
             + _rules(content, "not_an_address_rule", "not_an_address", ("address", "room")) + _rules(content, "address_level_rule", "address_level", ("address",)))
    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Regel-id måste vara unika; dubbletter: {', '.join(sorted({i for i in ids if ids.count(i) > 1}))}.")
    register = _need(content, "register", "filen")
    linkage = _need(content, "linkage", "filen")
    overlap = set(linkage.get("unique_values", [])) & set(linkage.get("ambiguous_values", [])) | set(linkage.get("unique_values", [])) & set(linkage.get("none_values", [])) \
        | set(linkage.get("ambiguous_values", [])) & set(linkage.get("none_values", []))
    if overlap:
        raise ValueError(f"Samma kopplingsstatus får bara tillhöra en grupp i [linkage]: {', '.join(sorted(overlap))}.")
    return QualityConfig(version=str(content.get("meta", {}).get("version", "")), columns=columns, register=dict(register), linkage=dict(linkage),
                         coverage=dict(content.get("coverage", {}).get("ladok", {})), rules=tuple(rules),
                         digest=hashlib.sha256(text.encode("utf-8")).hexdigest(), path=str(path))
