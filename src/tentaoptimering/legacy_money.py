"""Reading files from before the model counted in kronor.

Saved runs, scenario files and resource packs written earlier hold amounts in whole öre in keys that contain `_ore`
(`cost_ore`, `annual_cost_ore_per_staff`, parameter ids such as `cost.staff_annual_ore`). `upgrade` returns the same
document with the keys renamed to `_kr` and the amounts divided by 100. It only reads: the stored file is never changed, so
the manifest hashes of a run still describe the bytes on disk. A document without `_ore` keys is returned unchanged, so
upgrading twice does nothing.
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"(?<=[a-z0-9])_ore(?![a-z0-9])")
_UNIT = re.compile(r"\bore_per_")


def is_legacy_key(key: str) -> bool:
    return bool(_TOKEN.search(key))


def rename(key: str) -> str:
    return _TOKEN.sub("_kr", key)


def kronor(ore: Any) -> Any:
    """Whole öre to kronor; non-numbers (None, text) are returned as they are."""
    if isinstance(ore, bool) or not isinstance(ore, (int, float)):
        return ore
    whole, rest = divmod(int(round(ore)), 100)
    return whole if rest == 0 else round(int(round(ore)) / 100, 2)


def has_legacy_money(document: Any) -> bool:
    if isinstance(document, dict):
        return any(is_legacy_key(str(key)) or has_legacy_money(value) for key, value in document.items()) or _legacy_parameter(document)
    if isinstance(document, list):
        return any(has_legacy_money(item) for item in document)
    return False


def _legacy_parameter(row: dict[str, Any]) -> bool:
    return isinstance(row.get("parameter_id"), str) and is_legacy_key(row["parameter_id"])


def upgrade(document: Any) -> Any:
    """The document with öre keys and amounts converted to kronor (a copy; the argument is not changed)."""
    if isinstance(document, list):
        return [upgrade(item) for item in document]
    if not isinstance(document, dict):
        return document
    legacy_row = _legacy_parameter(document)
    result: dict[str, Any] = {}
    for key, value in document.items():
        text = str(key)
        if is_legacy_key(text):
            result[rename(text)] = kronor(value) if not isinstance(value, (dict, list)) else upgrade(value)
        elif legacy_row and text in ("value", "default", "scenario_value", "effective_value", "default_value") and not isinstance(value, (dict, list)):
            result[text] = kronor(value)
        elif legacy_row and text == "parameter_id":
            result[text] = rename(value)
        elif text == "unit" and isinstance(value, str) and _UNIT.search(value):
            result[text] = _UNIT.sub("kr_per_", value)
        else:
            result[text] = upgrade(value)
    return result


def upgrade_parameters(parameters: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The `[parameters]` table of an old scenario file: `cost.*_ore` ids become `_kr` with the amount in kronor.

    Returns the new table and the ids that were converted, so the caller can say so.
    """
    converted: list[str] = []
    result: dict[str, Any] = {}
    for key, value in parameters.items():
        if is_legacy_key(key):
            converted.append(key)
            result[rename(key)] = kronor(value)
        else:
            result[key] = value
    return result, converted


def loads(text: str) -> Any:
    """`json.loads` followed by `upgrade`: the way a saved run file is read."""
    import json

    return upgrade(json.loads(text))


def upgrade_scenario(content: dict[str, Any]) -> dict[str, Any]:
    """A scenario file from before kronor: `cost.*_ore` ids in `[parameters]` (amounts in öre) and `[rationales]` become `_kr` in kronor."""
    result = dict(content)
    if isinstance(content.get("parameters"), dict):
        result["parameters"], _converted = upgrade_parameters(content["parameters"])
    if isinstance(content.get("rationales"), dict):
        result["rationales"] = {rename(str(key)): value for key, value in content["rationales"].items()}
    return result
