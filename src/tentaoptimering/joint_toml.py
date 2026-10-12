"""Write a joint scenario (schema joint-real-subset-v1) back to TOML.

The scenario files use quoted dotted keys (`"staffing.ladder" = [...]`) and lists of inline tables, which the
generic writer in `app_storage` does not produce. This writer covers what a scenario contains: top-level values,
one level of tables, and values that are scalars, lists or inline tables. Reading the result with `tomllib` gives
back the content that was written.
"""

from __future__ import annotations

from datetime import date
import json
import math
import re
from typing import Any

_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _key(key: str) -> str:
    return key if _BARE_KEY.fullmatch(key) else json.dumps(key, ensure_ascii=False)


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Värdet kan inte sparas i TOML: {value!r}")
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{_key(str(name))} = {_value(item)}" for name, item in value.items()) + "}"
    raise ValueError(f"Värdet kan inte sparas i TOML: {value!r}")


def dump_scenario(content: dict[str, Any]) -> str:
    """TOML text for a scenario: top-level values first, then each table in the order given."""
    lines = [f"{_key(str(name))} = {_value(item)}" for name, item in content.items() if not isinstance(item, dict)]
    for name, table in content.items():
        if isinstance(table, dict):
            lines += ["", f"[{_key(str(name))}]"]
            lines += [f"{_key(str(entry))} = {_value(item)}" for entry, item in table.items()]
    return "\n".join(lines).strip() + "\n"
