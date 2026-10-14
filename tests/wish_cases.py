"""Test data for the business's wishes: a prepared `exam_wishes.csv` for synthetic datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNS = ["exam_event_id", "exam_order_id", "requested_date", "reserve_date_1", "reserve_date_2", "no_reserve_date_reason", "wish_status",
           "reason_has_letters", "booked_date", "booked_date_rank", "order_event_count", "wish_conflict"]


def wish_row(event: str, requested: str | None, reserve_1: str | None = None, reserve_2: str | None = None, reason: str | None = None,
             booked: str | None = None) -> dict[str, object]:
    """One exam event's wish. The status and the rank of the booked date follow the same rules as `wishes.py`."""
    if requested is None:
        status = "no_request"
    elif reserve_1 or reserve_2:
        status = "reserves_given"
    else:
        status = "reason_only" if reason else "neither"
    dates = (requested, reserve_1, reserve_2)
    rank = "not_booked" if booked is None else next((name for name, day in zip(("first", "reserve_1", "reserve_2"), dates) if day == booked), "other")
    return {"exam_event_id": event, "exam_order_id": f"order-{event}", "requested_date": requested or "", "reserve_date_1": reserve_1 or "",
            "reserve_date_2": reserve_2 or "", "no_reserve_date_reason": reason or "", "wish_status": status,
            "reason_has_letters": bool(reason and any(c.isalpha() for c in reason)), "booked_date": booked or "", "booked_date_rank": rank,
            "order_event_count": 1, "wish_conflict": False}


def write_wishes(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows, columns=COLUMNS).to_csv(path / "exam_wishes.csv", index=False, encoding="utf-8-sig")
