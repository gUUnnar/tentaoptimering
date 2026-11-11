"""Whole-facility hires in the explained difference between two alternatives (Fyrishov hired as one block per period).

The per-room rows show a hall's own charges; a hire window is not a room charge, so it is listed separately and the cost of
all windows is part of the external hire post. Using fewer halls inside a window does not change its cost; leaving the
whole window unused does.
"""

from __future__ import annotations

from typing import Any

from .abc_ledger import Ledger
from .joint_hire import active_windows, reserved_room_days
from .money import kdiff


def hire_window_rows(left: Ledger, right: Ledger) -> list[dict[str, Any]]:
    """One row per hire window in either alternative: whether it is hired in each and what that costs, in öre."""
    rows = []
    for window_id in sorted({w.window_id for ledger in (left, right) for w in ledger.problem.hire_windows}):
        sides = {}
        for key, ledger in (("left", left), ("right", right)):
            window = next((w for w in ledger.problem.hire_windows if w.window_id == window_id), None)
            used = [(s.room_id, s.day) for s in ledger.sessions] + reserved_room_days(ledger.problem)
            hired = bool(window and active_windows([window], used))
            sides[key] = {"hired": hired, "cost_kr": window.cost_kr if hired and window else 0, "known": window is not None}
        meta = next(w for ledger in (right, left) for w in ledger.problem.hire_windows if w.window_id == window_id)
        status = "kept" if sides["left"]["hired"] and sides["right"]["hired"] else "avoidable" if sides["left"]["hired"] else "added" if sides["right"]["hired"] else "unused"
        rows.append({
            "window_id": window_id, "name": meta.name, "start": meta.start.isoformat(), "end": meta.end.isoformat(), "origin": meta.origin,
            "room_ids": list(meta.room_ids), "parts": [dict(part) for part in meta.parts], "status": status, "left": sides["left"], "right": sides["right"],
            "difference_kr": kdiff(sides["right"]["cost_kr"], sides["left"]["cost_kr"]),
        })
    return rows
