"""Routes for the read-only booking views (`/api/bookings/...`). They read the prepared data and never start a run."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query

from . import booking_compare, booking_overview, booking_views
from .app_storage import AppStorage

ISO = r"^\d{4}-\d{2}-\d{2}$"


def _guard(call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return call()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def register_booking_routes(app: FastAPI, storage: AppStorage) -> None:
    @app.get("/api/bookings/locations")
    def booking_locations() -> dict[str, Any]:
        """Places (room or address) with bookings, and what the booking data covers."""
        return _guard(lambda: booking_views.locations_payload(storage.processed_dir))

    @app.get("/api/bookings/location")
    def booking_location(location: str = Query(..., min_length=1, max_length=200), date_from: str = Query(..., pattern=ISO),
                         date_to: str = Query(..., pattern=ISO)) -> dict[str, Any]:
        """The bookings of one place in a date range, with measures and their definitions."""
        return _guard(lambda: booking_views.location_payload(storage.processed_dir, location, date.fromisoformat(date_from), date.fromisoformat(date_to)))

    @app.get("/api/bookings/exams")
    def booking_exams(q: str = Query("", max_length=100), date_from: str | None = Query(None, pattern=ISO),
                      date_to: str | None = Query(None, pattern=ISO), limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
        """Search booked exams by id, course code or course name, optionally within a date range."""
        return _guard(lambda: booking_views.search_exams(storage.processed_dir, q, _day(date_from), _day(date_to), limit))

    @app.get("/api/bookings/exams/{order_id}")
    def booking_exam(order_id: str) -> dict[str, Any]:
        """One booked exam with all its placements."""
        return _guard(lambda: booking_views.exam_payload(storage.processed_dir, order_id))

    @app.get("/api/bookings/overview")
    def booking_overview_route(date_from: str = Query(..., pattern=ISO), date_to: str = Query(..., pattern=ISO),
                               address: str | None = Query(None, max_length=200)) -> dict[str, Any]:
        """Bookings in a period per address and room; with `address` (empty = bookings without an address) all bookings there."""
        return _guard(lambda: booking_overview.overview_payload(storage.processed_dir, date.fromisoformat(date_from), date.fromisoformat(date_to), address))

    @app.get("/api/bookings/exams/{order_id}/compare")
    def booking_compare_route(order_id: str, run: str = Query(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")) -> dict[str, Any]:
        """A booked exam next to its placement in a saved run (through the provisional Ladok link)."""
        return _guard(lambda: booking_compare.compare_payload(storage, order_id, run))
