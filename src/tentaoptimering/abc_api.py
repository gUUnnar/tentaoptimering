"""Routes for A/B/C (`/api/abc/...`): the run list, a profile, a comparison and the state of the business's wishes.

They read saved files and the prepared underlay and never start a run.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query

from . import abc_compare
from .app_storage import AppStorage

REF = r"^(actual|[A-Za-z0-9][A-Za-z0-9_.-]{0,159})$"
ISO = r"^\d{4}-\d{2}-\d{2}$"


def _guard(call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return call()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def register_abc_routes(app: FastAPI, storage: AppStorage) -> None:
    @app.get("/api/abc/runs")
    def abc_runs() -> dict[str, Any]:
        """Saved runs with name, kind (B or C), base run and whether they were built on the current underlay."""
        return _guard(lambda: {"runs": abc_compare.list_runs(storage)})

    @app.get("/api/abc/profile")
    def abc_profile(ref: str = Query(..., pattern=REF), scope_run: str | None = Query(None, pattern=REF),
                    date_from: str | None = Query(None, pattern=ISO), date_to: str | None = Query(None, pattern=ISO),
                    include_exams: bool = Query(True)) -> dict[str, Any]:
        """A (`actual`, for the exams of `scope_run` or a period) or a saved run, in one shape. Without exams: the summary only."""
        return _guard(lambda: abc_compare.profile(storage, ref, scope_run, date_from, date_to, include_exams))

    @app.get("/api/abc/compare")
    def abc_compare_route(left: str = Query(..., pattern=REF), right: str = Query(..., pattern=REF)) -> dict[str, Any]:
        """Two profiles side by side: metrics, wishes, changes, rooms, utilisation, cost by kind and parameter differences."""
        return _guard(lambda: abc_compare.compare(storage, left, right))

    @app.get("/api/abc/wishes")
    def abc_wishes() -> dict[str, Any]:
        """How complete the business's wishes (requested and reserve dates, reasons) are in the prepared underlay."""
        return _guard(lambda: abc_compare.wishes_summary(storage))
