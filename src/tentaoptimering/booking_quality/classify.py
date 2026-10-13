"""Classify booking rows along four independent dimensions. A row has a value on each; they are not one mutually exclusive state.

* **Resource identification**: what the data identifies, not why something is missing.
  `room_matched` (a named room that is in the room register), `room_named_not_in_register`, `address_only` (an address, no room),
  `no_address`, `declared_non_physical` (a *verified* rule says the place is not a physical room).
* **Data quality**: a list of findings (`flags`) about the row, each a plain fact (`room_missing`, `places_exceed_capacity`, ...).
  Which findings an explanation might apply to is never decided here: `declared_address_level` is true only when a *verified*
  rule says so.
* **Source coverage**: whether the booking date lies inside the period another source covers (`ladok_coverage`).
* **Link certainty**: how firm the link from a booking to a Ladok activity is (`link_certainty`).

Unverified rules never classify; a row that matches one gets its id in `candidate_rule_ids`. Cancelled rows are classified like
others, but findings about date, time and places are only raised for rows that are not cancelled. Nothing here is read by the
optimisation engine, and the result does not decide blocking, capacity reduction or approval.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .config import QualityConfig

TIME = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")
IDENTIFICATIONS = ("room_matched", "room_named_not_in_register", "address_only", "no_address", "declared_non_physical")
LINKS = ("unique", "ambiguous", "none_within_coverage", "none_outside_coverage", "none_coverage_unknown", "not_assessed")


def ladok_window(config: QualityConfig, ladok: pd.DataFrame | None) -> dict[str, Any]:
    """The period the Ladok source covers: the configured override, else first and last date in the data, else unknown."""
    first, last = config.coverage.get("override_first"), config.coverage.get("override_last")
    if first and last:
        return {"first": str(first), "last": str(last), "origin": "override"}
    column = config.coverage.get("date_column", "")
    if ladok is not None and column in ladok:
        dates = ladok[column].astype(str).str.strip()
        dates = dates[dates != ""]
        if len(dates):
            return {"first": dates.min(), "last": dates.max(), "origin": "derived"}
    return {"first": None, "last": None, "origin": "unknown"}


def _link_table(config: QualityConfig, linkage: pd.DataFrame | None) -> dict[str, str] | None:
    """Per placement: `unique`, `ambiguous` or `none`. Rule: no candidate rows is `none`; more than one distinct activity, or any ambiguous
    row, is `ambiguous`; exactly one activity from unique rows is `unique`. The rule does not depend on the order of the rows."""
    if linkage is None:
        return None
    cfg = config.linkage
    unique, ambiguous = set(cfg.get("unique_values", [])), set(cfg.get("ambiguous_values", []))
    result: dict[str, str] = {}
    for placement, group in linkage.groupby(cfg["placement_id"]):
        statuses = set(group[cfg["status"]])
        activities = {a for a in group[cfg["activity_id"]] if a}
        if statuses & ambiguous or len(activities) > 1:
            result[placement] = "ambiguous"
        elif len(activities) == 1 and statuses & unique:
            result[placement] = "unique"
        else:
            result[placement] = "none"
    return result


def classify(bookings: pd.DataFrame, config: QualityConfig, register: pd.DataFrame | None = None, linkage: pd.DataFrame | None = None,
             ladok: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per booking row, same order, with the four dimensions. All inputs are text (`dtype=str`, no NaN)."""
    col = config.columns
    reg = config.register
    in_register: dict[str, str] = {}
    if register is not None:
        usable = register[register[reg["room_id"]] != ""]
        in_register = dict(zip(usable[reg["location_key"]], usable[reg["capacity"]]))
    window = ladok_window(config, ladok)
    links = _link_table(config, linkage)
    status_rules = config.rules_of("status")
    non_physical, not_address, address_level = config.rules_of("non_physical"), config.rules_of("not_an_address"), config.rules_of("address_level")
    out: list[dict[str, Any]] = []
    for row in bookings.to_dict("records"):
        address, room, key, status = row[col["address"]].strip(), row[col["room"]].strip(), row[col["location_key"]].strip(), row[col["status"]].strip()
        values = {"address": address, "room": room, "status": status}
        candidates: list[str] = []
        flags: list[str] = []

        verified_np = [r for r in non_physical if r.verified and r.matches(values)]
        verified_na = [r for r in not_address if r.verified and r.matches(values)]
        candidates += [r.id for r in non_physical + not_address if not r.verified and r.matches(values)]
        capacity: int | None = None
        if verified_np:
            identification = "declared_non_physical"
        elif verified_na:
            identification, flags = "no_address", flags + ["address_field_not_an_address"]
        elif not address:
            identification = "no_address"
        elif not room:
            identification, flags = "address_only", flags + ["room_missing"]
        elif key in in_register:
            identification = "room_matched"
            capacity = int(in_register[key]) if in_register[key].isdigit() else None
            if capacity is None:
                flags.append("capacity_missing_in_register")
        else:
            identification, flags = "room_named_not_in_register", flags + ["room_not_in_register"]
        declared = [r.id for r in address_level if r.verified and r.matches(values)] if identification == "address_only" else []

        matched_status = [r for r in status_rules if r.verified and r.matches(values)]
        candidates += [r.id for r in status_rules if not r.verified and r.matches(values)]
        status_class = matched_status[0].value_class if matched_status else "unclassified"

        date = row[col["date"]].strip()
        if status_class != "cancelled":
            if not date:
                flags.append("date_missing")
            if not TIME.match(row[col["time"]].strip()):
                flags.append("time_unparseable")
            places = row[col["places"]].strip()
            if not places.isdigit() or int(places) == 0:
                flags.append("places_missing_or_zero")
            elif capacity is not None and int(places) > capacity:
                flags.append("places_exceed_capacity")
            if status_class == "unclassified":
                flags.append("status_unclassified")

        if not window["first"] or not date:
            coverage = "unknown"
        else:
            coverage = "within" if window["first"] <= date <= window["last"] else "outside"
        if links is None:
            link = "not_assessed"
        else:
            kind = links.get(row[col["placement_id"]], "none")
            link = kind if kind != "none" else {"within": "none_within_coverage", "outside": "none_outside_coverage"}.get(coverage, "none_coverage_unknown")
            link = {"unique": "unique", "ambiguous": "ambiguous"}.get(kind, link)
        out.append({"placement_id": row[col["placement_id"]], "resource_identification": identification, "declared_address_level": bool(declared),
                    "declared_by": declared, "capacity": capacity, "status_class": status_class, "flags": flags, "candidate_rule_ids": sorted(set(candidates)),
                    "ladok_coverage": coverage, "link_certainty": link})
    return pd.DataFrame(out, index=bookings.index)
