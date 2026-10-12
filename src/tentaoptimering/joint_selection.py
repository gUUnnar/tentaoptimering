"""Which exam events a joint scenario covers: a named list of events or a rule over the prepared data.

A scenario's `[subset]` table says it in exactly one of two ways:

* `exam_event_ids = [...]`: the named events, no more and no fewer (every one must be ready for modelling);
* `selection = "all_ready"`: every event that is ready for modelling in `plan_area`, optionally only those whose
  historical date lies in `date_from`..`date_to` (ISO dates, inclusive).

The rule is resolved against the data at build time, so the same scenario file follows the prepared data without
a list that has to be kept up to date. The result is still an explicit, sorted set of events that the run records.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

READY_STATUS = "ready_provisional_ladok_demand"
RULE_ALL_READY = "all_ready"


def subset_kind(subset: dict[str, Any]) -> str:
    """`event_list` or `rule`; anything else (neither or both) is a configuration error in Swedish."""
    has_list, has_rule = "exam_event_ids" in subset, "selection" in subset
    if has_list == has_rule:
        raise ValueError("Urvalet måste ange antingen exam_event_ids (namngivna tentor) eller selection (regel), inte båda och inte ingen.")
    if has_list:
        extra = [key for key in ("date_from", "date_to") if key in subset]
        if extra:
            raise ValueError(f"{', '.join(extra)} kan bara användas tillsammans med selection.")
        return "event_list"
    if subset["selection"] != RULE_ALL_READY:
        raise ValueError(f"Okänd urvalsregel: {subset['selection']!r}. Tillåtet värde: {RULE_ALL_READY!r}.")
    return "rule"


def date_window(subset: dict[str, Any]) -> tuple[str | None, str | None]:
    """The rule's date limits as ISO strings (None where open); an invalid or reversed window is an error."""
    limits = []
    for key in ("date_from", "date_to"):
        value = subset.get(key)
        if value in (None, ""):
            limits.append(None)
            continue
        try:
            limits.append(date.fromisoformat(str(value)).isoformat())
        except ValueError as error:
            raise ValueError(f"{key} måste vara ett ISO-datum (ÅÅÅÅ-MM-DD), inte {value!r}.") from error
    if limits[0] and limits[1] and limits[0] > limits[1]:
        raise ValueError("date_from får inte vara senare än date_to.")
    return limits[0], limits[1]


def select_ready_demands(demands: pd.DataFrame, subset: dict[str, Any]) -> pd.DataFrame:
    """The ready demand rows of the scenario's events (a copy). Named events that are missing are an error."""
    ready = demands["demand_input_status"] == READY_STATUS
    if subset_kind(subset) == "event_list":
        selected = tuple(str(value) for value in subset["exam_event_ids"])
        rows = demands[demands["exam_event_id"].isin(selected) & ready].copy()
        found = set(rows["exam_event_id"].astype(str))
        if found != set(selected):
            raise ValueError(f"Det verkliga delmängdsfallet saknar event: {sorted(set(selected) - found)}")
        return rows
    first, last = date_window(subset)
    mask = ready & (demands["observed_cities"].astype(str) == str(subset["plan_area"]))
    days = demands["scheduled_date"].astype(str)
    if first:
        mask &= days >= first
    if last:
        mask &= days <= last
    rows = demands[mask].copy()
    if rows.empty:
        raise ValueError("Urvalsregeln gav inga tentor som är klara för modellering i det valda planeringsområdet och datumintervallet.")
    return rows


def describe_subset(subset: dict[str, Any], exam_count: int | None) -> str:
    """One Swedish sentence about what a scenario covers, for scenario lists."""
    area = str(subset.get("plan_area", ""))
    if subset_kind(subset) == "event_list":
        return f"{len(subset['exam_event_ids'])} namngivna tentor i {area}."
    first, last = date_window(subset)
    span = f" med ursprungsdatum {first or 'från början'} till {last or 'slutet'}" if first or last else ""
    count = f" ({exam_count} tentor)" if exam_count is not None else ""
    return f"Alla tentor som är klara för modellering i {area}{span}{count}."


def count_selected(demands: pd.DataFrame, subset: dict[str, Any]) -> int | None:
    """Number of events the subset covers in this data; None when the rule cannot be resolved."""
    try:
        return int(select_ready_demands(demands, subset)["exam_event_id"].nunique())
    except ValueError:
        return None
