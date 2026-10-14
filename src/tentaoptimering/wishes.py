"""The business's original wishes for each exam: requested date, two reserve dates and the reason for giving none.

The booking export carries these per exam order (`requested_date`, `reserve_date_1`, `reserve_date_2`,
`no_reserve_date_reason`). They are the *wish*, not the booking: the booking (`scheduled_date`, room, time) is what was
finally reserved, and the two are kept apart. A wish has dates only, never a time of day.

This module turns the export into one row per exam event (`exam_wishes.csv`, the grain of the optimisation demand) and
reports how complete the wishes are. Nothing is interpreted: the reason text is kept as it is, and the only things
derived from it are facts about the text itself (is there any, does it contain a letter). Whether a wish was
granted is stated by the rank of the booked date among the wish dates, never guessed.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

WISHES_FILE = "exam_wishes.csv"
EVENT_KEYS = ["exam_order_id", "scheduled_date", "scheduled_time"]
WISH_COLUMNS = ["requested_date", "reserve_date_1", "reserve_date_2"]
# Where a date lies among the wishes: in the business's order of priority, or not among them.
RANKS = ("first", "reserve_1", "reserve_2", "other")
STATUS_TEXT = {
    "reserves_given": "Reservdatum angivna.",
    "reason_only": "Inga reservdatum, men en motivering finns.",
    "neither": "Varken reservdatum eller motivering.",
    "no_request": "Önskat datum saknas.",
}
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


def _first_value(series: pd.Series) -> str | None:
    values = sorted({str(value).strip() for value in series.dropna() if str(value).strip()})
    return values[0] if values else None


def date_rank(day: str | None, wishes: tuple[str | None, str | None, str | None]) -> str:
    """`first`, `reserve_1`, `reserve_2` for a date that is a wish, `other` for any other date."""
    for rank, wished in zip(RANKS, wishes):
        if day is not None and wished is not None and day == wished:
            return rank
    return "other"


def reason_has_letters(text: str | None) -> bool:
    return bool(text) and _LETTER.search(str(text)) is not None


def build_exam_wishes(bookings: pd.DataFrame, exam_events: pd.DataFrame) -> pd.DataFrame:
    """One row per exam event with the wish of its exam order. An order shared by several events gives each the same wish."""
    for column in WISH_COLUMNS + ["no_reserve_date_reason"]:
        if column not in bookings:
            bookings = bookings.assign(**{column: pd.NA})
    columns = WISH_COLUMNS + ["no_reserve_date_reason"]
    per_order = bookings.groupby("exam_order_id", dropna=False).agg(**{column: (column, _first_value) for column in columns}).reset_index()
    conflict = (bookings.groupby("exam_order_id")[columns].nunique() > 1).any(axis=1)
    per_order["wish_conflict"] = per_order["exam_order_id"].map(conflict).fillna(False).astype(bool)
    events = exam_events[["exam_event_id", "exam_order_id", "scheduled_date"]].merge(per_order, on="exam_order_id", how="left")
    events["order_event_count"] = events.groupby("exam_order_id")["exam_event_id"].transform("size")
    events["wish_status"] = events.apply(_status, axis=1)
    events["reason_has_letters"] = events["no_reserve_date_reason"].map(reason_has_letters)
    events["booked_date_rank"] = events.apply(
        lambda row: "not_booked" if pd.isna(row["scheduled_date"]) else date_rank(
            str(row["scheduled_date"]), _wish_tuple(row)), axis=1)
    return events.rename(columns={"scheduled_date": "booked_date"})[[
        "exam_event_id", "exam_order_id", "requested_date", "reserve_date_1", "reserve_date_2", "no_reserve_date_reason",
        "wish_status", "reason_has_letters", "booked_date", "booked_date_rank", "order_event_count", "wish_conflict",
    ]]


def _wish_tuple(row: Any) -> tuple[str | None, str | None, str | None]:
    return tuple(None if pd.isna(row[column]) else str(row[column]) for column in WISH_COLUMNS)  # type: ignore[return-value]


def _status(row: Any) -> str:
    if pd.isna(row["requested_date"]):
        return "no_request"
    if not pd.isna(row["reserve_date_1"]) or not pd.isna(row["reserve_date_2"]):
        return "reserves_given"
    return "reason_only" if not pd.isna(row["no_reserve_date_reason"]) else "neither"


def summarize_wishes(wishes: pd.DataFrame) -> dict[str, Any]:
    """Counts that tell how much of the wish data can be used and what is missing. Orders are counted once."""
    orders = wishes.drop_duplicates("exam_order_id")
    status = orders["wish_status"].value_counts().to_dict()
    live = wishes[wishes["booked_date_rank"] != "not_booked"]
    return {
        "events": int(len(wishes)), "orders": int(len(orders)),
        "status": {key: int(status.get(key, 0)) for key in STATUS_TEXT},
        "reason_without_letters": int((orders["wish_status"].isin(["reason_only"]) & ~orders["reason_has_letters"]).sum()),
        "orders_with_conflicting_wishes": int(orders["wish_conflict"].sum()),
        "orders_with_several_events": int((orders["order_event_count"] > 1).sum()),
        "booked_date_rank": {key: int((live["booked_date_rank"] == key).sum()) for key in RANKS},
        "not_booked_events": int((wishes["booked_date_rank"] == "not_booked").sum()),
    }
