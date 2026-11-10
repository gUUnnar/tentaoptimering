"""Amounts in the validator: exact, in whole hundredths of a krona, with no import from the engine.

The saved files hold kronor with at most two decimals. The validator converts every amount it reads to whole hundredths (an
integer) with `units`, does all its arithmetic on integers, and compares with the reported amounts after converting those the same
way, so a cost either agrees to the öre or it does not. `upgrade` reads files from before the model counted in kronor
(keys with `_ore`, amounts in öre) as kronor, without changing the file.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any

_TOKEN = re.compile(r"(?<=[a-z0-9])_ore(?![a-z0-9])")


def units(value: Any, where: str = "belopp") -> int:
    """An amount in kronor as whole hundredths; ValueError if it is not a number with at most two decimals."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{where}: ett belopp i kronor förväntades, fick {value!r}")
    try:
        exact = Decimal(str(value)) * 100
    except InvalidOperation as error:
        raise ValueError(f"{where}: ogiltigt belopp {value!r}") from error
    if exact != exact.to_integral_value():
        raise ValueError(f"{where}: belopp i kronor får ha högst två decimaler, fick {value!r}")
    return int(exact)


def reported_units(value: Any) -> int | None:
    """Like `units` for a reported amount, or None when it is missing or not an exact amount (which then differs from any recomputation)."""
    if value is None:
        return None
    try:
        return units(value)
    except ValueError:
        return None


def text(hundredths: int) -> str:
    """An amount of whole hundredths as text in kronor."""
    whole, rest = divmod(abs(hundredths), 100)
    sign = "-" if hundredths < 0 else ""
    return f"{sign}{whole}" + (f",{rest:02d}" if rest else "") + " kr"


def _ore_to_kr(value: Any) -> Any:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    whole, rest = divmod(int(round(value)), 100)
    return whole if rest == 0 else round(int(round(value)) / 100, 2)


def upgrade(document: Any) -> Any:
    """The document with `_ore` keys renamed to `_kr` and their amounts divided by 100 (a copy); a document without such keys is unchanged."""
    if isinstance(document, list):
        return [upgrade(item) for item in document]
    if not isinstance(document, dict):
        return document
    legacy_row = isinstance(document.get("parameter_id"), str) and bool(_TOKEN.search(document["parameter_id"]))
    result: dict[str, Any] = {}
    for key, value in document.items():
        name = str(key)
        scalar = not isinstance(value, (dict, list))
        if _TOKEN.search(name):
            result[_TOKEN.sub("_kr", name)] = _ore_to_kr(value) if scalar else upgrade(value)
        elif legacy_row and name == "parameter_id":
            result[name] = _TOKEN.sub("_kr", value)
        elif legacy_row and name in ("value", "default", "scenario_value", "effective_value", "default_value") and scalar:
            result[name] = _ore_to_kr(value)
        else:
            result[name] = upgrade(value)
    return result
