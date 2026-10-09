"""Transparent, deliberately non-comparable cost views for term runs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def preliminary_cost_comparison(processed_dir: Path, scenario_cost_ore: int | None) -> dict[str, object]:
    """Expose the available baseline profile without labelling it as a saving.

    Lease rows are mixed contract objects and have no verified link to the rooms
    chosen by the scenario.  Their internal-rent sum is therefore useful context,
    but not a comparable baseline or an avoidable cost.
    """
    lease_path = processed_dir / "lease_rows.csv"
    if scenario_cost_ore is None or not lease_path.is_file():
        return _blocked(None, scenario_cost_ore)
    frame = pd.read_csv(lease_path, encoding="utf-8-sig")
    column = "annual_internal_rent_prelim_2026_sek"
    if column not in frame:
        return _blocked(None, scenario_cost_ore)
    baseline_ore = int(round(float(pd.to_numeric(frame[column], errors="coerce").sum()) * 100))
    return {
        "status": "not_comparable",
        "source_baseline_preliminary_internal_rent_ore": baseline_ore,
        "scenario_assumption_cost_ore": scenario_cost_ore,
        "theoretical_annual_potential_ore": None,
        "verified_realizable_saving_ore": None,
        "blocking_reasons": _reasons(),
    }


def _blocked(baseline_ore: int | None, scenario_cost_ore: int | None) -> dict[str, object]:
    return {
        "status": "not_evaluated",
        "source_baseline_preliminary_internal_rent_ore": baseline_ore,
        "scenario_assumption_cost_ore": scenario_cost_ore,
        "theoretical_annual_potential_ore": None,
        "verified_realizable_saving_ore": None,
        "blocking_reasons": _reasons(),
    }


def _reasons() -> list[str]:
    return [
        "Lokal- och avtalsrader har inte verifierad koppling till scenario-rum.",
        "Källans internhyra är inte klassificerad som undvikbar kostnad.",
        "Scenarioresultatet använder ersättbara lokal- och personalkostnadsproxyer.",
        "Uppsägningstid, realiseringsdatum och engångskostnader saknas.",
    ]
