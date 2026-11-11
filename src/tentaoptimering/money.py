"""Money in kronor, with whole öre only inside the solver.

Every amount of the model (parameters, resource data, contract fields, results, reports, API) is in kronor with at most two
decimals. CP-SAT needs whole numbers, so a cost term is turned into solver units (hundredths of a krona) in exactly one
place per term with `to_units`, and a cost that comes out of the solver goes back with `from_units`. No other code
multiplies or divides by 100.
"""

from __future__ import annotations

import math
from typing import Any

UNITS_PER_KR = 100
# Floating-point noise on an amount with two decimals is far below this; an amount such as 1e-15 kr is not noise but a third decimal.
_ABSOLUTE_TOLERANCE = 1e-14
_RELATIVE_TOLERANCE = 1e-12


def has_at_most_two_decimals(value: float) -> bool:
    scaled = value * UNITS_PER_KR
    return abs(scaled - round(scaled)) <= max(_ABSOLUTE_TOLERANCE, _RELATIVE_TOLERANCE * abs(scaled))


def check_kr(value: Any, where: str) -> float | int:
    """The amount as a number, or a ValueError (Swedish) when it is not a finite number with at most two decimals."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{where}: ett belopp i kronor förväntades, fick {value!r}.")
    if not has_at_most_two_decimals(value):
        raise ValueError(f"{where}: belopp i kronor får ha högst två decimaler, fick {value!r}.")
    return value


def to_units(kr: float | int) -> int:
    """Kronor to whole solver units (hundredths of a krona)."""
    return int(round(kr * UNITS_PER_KR))


def from_units(units: int | float) -> float | int:
    """Solver units to kronor: a whole number of kronor stays an integer, otherwise two decimals."""
    whole, rest = divmod(int(round(units)), UNITS_PER_KR)
    return whole if rest == 0 else round(int(round(units)) / UNITS_PER_KR, 2)


def ksum(values) -> float | int:
    """An exact sum of amounts in kronor (summed in solver units, so that no floating-point noise reaches a comparison)."""
    return from_units(sum(to_units(value) for value in values))


def kdiff(left: float | int, right: float | int) -> float | int:
    """An exact difference of two amounts in kronor."""
    return from_units(to_units(left) - to_units(right))


def kmul(rate: float | int, count: int | float) -> float | int:
    """An exact amount times a count (for example a price per minute times the paid minutes)."""
    return from_units(to_units(rate) * count)


def kr(value: float | int) -> float | int:
    """An amount normalised to the representation that is written to files (two decimals, integer when whole)."""
    return from_units(to_units(value))
