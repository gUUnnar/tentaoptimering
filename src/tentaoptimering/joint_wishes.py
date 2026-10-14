"""The business's wishes as input to a joint run: which dates an exam may use when wishes steer the calendar.

`exam_wishes.csv` (see `wishes.py`) holds, per exam event, the requested date, the two reserve dates and the reason given
when there are none. Three parameters decide how a run uses them:

* `wish.candidate_policy`: `window` (the days around the booked date, the original behaviour), `wishes` (only the
  requested date and the reserve dates the business wrote down) or `wishes_and_window` (both);
* `wish.time_policy`: the wishes are dates only, so an exam either keeps its booked start time on a wished date
  (`booked_start`) or may use any allowed start time that day (`any_start`);
* `wish.tiebreak`: see `joint_preference`.

Nothing is assumed about an exam without wishes or whose wished dates the calendar does not allow: it simply has fewer
(possibly no) candidate occasions, and a run says so as an unplaceable exam instead of widening the choice by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .wishes import WISHES_FILE

WINDOW, WISHES, WISHES_AND_WINDOW = "window", "wishes", "wishes_and_window"
BOOKED_START, ANY_START = "booked_start", "any_start"
NOT_LOADED, NOT_IN_DATA = "not_loaded", "not_in_data"


@dataclass(frozen=True)
class EventWish:
    dates: tuple[str | None, str | None, str | None]  # requested, reserve 1, reserve 2
    status: str
    reason: str | None = None

    def days(self) -> list[date]:
        """The wished dates in order of priority, each once."""
        found: list[date] = []
        for item in self.dates:
            if item is not None and date.fromisoformat(item) not in found:
                found.append(date.fromisoformat(item))
        return found


def uses_wishes(policy: str) -> bool:
    return policy in (WISHES, WISHES_AND_WINDOW)


def uses_window(policy: str) -> bool:
    return policy in (WINDOW, WISHES_AND_WINDOW)


def load_wishes(processed_dir: Path) -> dict[str, EventWish] | None:
    """Wish per exam event, or None when the prepared underlay has no wishes (it was prepared before they were read)."""
    path = processed_dir / WISHES_FILE
    if not path.is_file():
        return None
    frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    return {
        row.exam_event_id: EventWish(
            (row.requested_date or None, row.reserve_date_1 or None, row.reserve_date_2 or None),
            row.wish_status, row.no_reserve_date_reason or None)
        for row in frame.itertuples(index=False)
    }


def require_wishes(wishes: dict[str, EventWish] | None, values: dict[str, Any]) -> None:
    """A policy or tie-break that depends on the wishes needs them in the underlay: refuse instead of running without."""
    needs = uses_wishes(str(values["wish.candidate_policy"])) or values["wish.tiebreak"] == "wish_priority"
    if needs and wishes is None:
        raise ValueError(
            "Underlaget innehåller inte verksamhetens önskemål (exam_wishes.csv). Förbered underlaget igen under Underlag, "
            "eller välj fönster kring bokat datum och färst ändringar som avgörande.")


def wish_for(wishes: dict[str, EventWish] | None, event_id: str) -> EventWish:
    if wishes is None:
        return EventWish((None, None, None), NOT_LOADED)
    return wishes.get(event_id, EventWish((None, None, None), NOT_IN_DATA))


def wish_candidate_ids(
    event: dict[str, Any], slots: tuple[Any, ...], policy: str, time_policy: str, latest_end: int,
) -> set[str]:
    """Slot ids on the wished dates (allowed by the calendar) that the exam fits; none for a policy without wishes."""
    if not uses_wishes(policy):
        return set()
    wished = set(event["wish"].days())
    return {
        slot.slot_id for slot in slots
        if not slot.reference_only and slot.scheduled_date in wished
        and (time_policy == ANY_START or slot.start_minute == event["original_start"])
        and slot.start_minute + event["duration"] <= latest_end
    }
