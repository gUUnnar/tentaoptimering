from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CostComponent:
    """En kostnadspost med tydlig realiserbarhet och tidsprofil."""

    component_id: str
    name: str
    annual_amount_sek: Decimal | None
    cost_type: str
    avoidable: bool | None
    earliest_realization_date: str | None
    one_off_cost_sek: Decimal | None
    source_reference: str | None


@dataclass(frozen=True)
class SavingsResult:
    """Resultatbehållare. Den fylls först när kostnadskopplingarna är verifierade."""

    reduced_capacity_need: int | None
    changed_internal_allocation_sek: Decimal | None
    potentially_realizable_saving_sek: Decimal | None
    realization_date: str | None
    blocking_reasons: tuple[str, ...]


REQUIRED_COST_FIELDS = (
    "stable_room_id",
    "contract_object_id",
    "avoidable_cost_sek",
    "notice_period",
    "earliest_realization_date",
    "one_off_cost_sek",
)


def uncalculated_savings() -> SavingsResult:
    return SavingsResult(
        reduced_capacity_need=None,
        changed_internal_allocation_sek=None,
        potentially_realizable_saving_sek=None,
        realization_date=None,
        blocking_reasons=(
            "Salar saknar verifierad koppling till avtalsobjekt.",
            "Källan skiljer inte intern kostnadsfördelning från undvikbar universitetskostnad.",
            "Uppsägningstid, realiseringsdatum och engångskostnader saknas.",
        ),
    )
