"""Single catalog used to expose, freeze and declare support for business parameters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any

from .joint_contract import ParameterValue


SUPPORT_STATES = {"implemented", "contract_only"}
BASIS_STATES = {"verified", "source_data", "assumption", "experiment"}


@dataclass(frozen=True)
class ParameterDefinition:
    parameter_id: str
    group: str
    label: str
    value_type: str
    unit: str
    default: Any
    default_basis: str
    help_text: str
    engine_support: str
    honored_by: str | None
    legacy_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParameterCatalog:
    version: str
    parameters: tuple[ParameterDefinition, ...]


def load_parameter_catalog(path: Path) -> ParameterCatalog:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    definitions = tuple(
        ParameterDefinition(
            parameter_id=str(item["id"]),
            group=str(item["group"]),
            label=str(item["label"]),
            value_type=str(item["value_type"]),
            unit=str(item.get("unit", "")),
            default=item.get("default"),
            default_basis=str(item["default_basis"]),
            help_text=str(item["help_text"]),
            engine_support=str(item["engine_support"]),
            honored_by=str(item["honored_by"]) if item.get("honored_by") else None,
            legacy_ids=tuple(str(value) for value in item.get("legacy_ids", ())),
        )
        for item in payload["parameter"]
    )
    ids = [item.parameter_id for item in definitions]
    if not payload.get("catalog_version") or len(ids) != len(set(ids)):
        raise ValueError("Parameterkatalogen kräver version och unika parameter-id:n.")
    for item in definitions:
        if item.engine_support not in SUPPORT_STATES:
            raise ValueError(f"Okänt motorstödstillstånd för {item.parameter_id}.")
        if item.default_basis not in BASIS_STATES:
            raise ValueError(f"Okänd standardgrund för {item.parameter_id}.")
        if item.engine_support == "implemented" and not item.honored_by:
            raise ValueError(f"Implementerad parameter saknar honored_by: {item.parameter_id}.")
    return ParameterCatalog(str(payload["catalog_version"]), definitions)


def freeze_parameter_values(
    catalog: ParameterCatalog,
    overrides: dict[str, Any] | None = None,
    rationales: dict[str, str] | None = None,
) -> tuple[ParameterValue, ...]:
    overrides = overrides or {}
    rationales = rationales or {}
    known = {item.parameter_id for item in catalog.parameters}
    unknown = set(overrides) - known
    if unknown:
        raise ValueError(f"Okända verksamhetsparametrar: {sorted(unknown)}")
    values = []
    for item in catalog.parameters:
        overridden = item.parameter_id in overrides
        value = overrides.get(item.parameter_id, item.default)
        basis = (
            "experiment"
            if overridden and item.default_basis in {"verified", "source_data"}
            else item.default_basis
        )
        rationale = rationales.get(
            item.parameter_id,
            "Scenariovärde för avgränsad körning." if overridden else "Katalogens standardvärde.",
        )
        if basis == "assumption" and not rationale.strip():
            raise ValueError(f"Antagandet {item.parameter_id} kräver motivering.")
        values.append(
            ParameterValue(
                item.parameter_id, value, basis, rationale, item.engine_support,
                changed_from_default=overridden and value != item.default,
            )
        )
    return tuple(values)
