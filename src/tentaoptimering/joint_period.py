"""Choosing the planning period of a joint run: coverage of the data, a check of the chosen period, and the scenario it gives.

The user picks a start and an end date in the interface; no scenario file has to be edited. What may be chosen is
decided by the data, not by a term length:

* the *demand* coverage (Ladok participants) is the dates of the prepared exam demands. Only exams in this window can be
  optimised, and a period that reaches outside it is planned only for the part inside (and says so);
* the *booking* coverage is shown for information; bookings alone give no demand and so cannot be optimised.

An exam belongs to the period when its historical date lies in `date_from`..`date_to` (inclusive). The calendar of the
run is cut to the same dates, so an exam never moves out of the period: a boundary exam has less room to move, which
the report states. Exams that are not ready for modelling (missing demand) are counted and never silently dropped.

Every period run is *exploratory*: the model does not know about bookings that are outside the chosen exams, so a
room that is free in the result may in reality be taken. `PLANNING_BASIS` says so in words the interface repeats.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel

from .joint_selection import READY_STATUS, RULE_ALL_READY, subset_kind

DEMANDS_FILE, BOOKINGS_FILE = "optimization_demands.csv", "bookings.csv"

PLANNING_BASIS: dict[str, Any] = {
    "mode": "exploratory",
    "fixed_bookings_considered": False,
    "label": "Explorativ planering",
    "note": ("Modellen känner inte till bokningar som ligger utanför de valda tentorna. Ett resultat visar därför inte att en sal "
             "är ledig i verkligheten: salens verkliga tillgänglighet måste kontrolleras mot bokningssystemet."),
    "cost_name": "Modellerad årlig kapacitetskostnad för valt urval",
    "cost_note": ("Kostnaden är modellens årliga kapacitetskostnad för det valda urvalet: lokalerna som behövs (platser gånger årspris) och "
                  "vaktpoolen, som dimensioneras efter toppbelastningen. Den är inte kostnaden för perioden och inte faktisk kostnad. "
                  "Kostnader för olika urval är inte jämförbara och får inte skalas upp till en årlig besparing."),
}


class PeriodRequest(BaseModel):
    date_from: date
    date_to: date
    # A period that reaches outside the demand data is planned only if the user has accepted the shorter period.
    accept_partial: bool = False


class PeriodError(ValueError):
    """The chosen period cannot be planned; the message is the reason in Swedish."""


def _read(processed_dir: Path, name: str) -> pd.DataFrame | None:
    path = processed_dir / name
    if not path.is_file():
        return None
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except (OSError, ValueError):
        return None


def _area(demands: pd.DataFrame, plan_area: str) -> pd.DataFrame:
    return demands[demands["observed_cities"].astype(str) == plan_area]


def coverage_payload(processed_dir: Path, plan_area: str) -> dict[str, Any]:
    """What the data allows: the demand window, the days with exams and the (informational) booking window."""
    demands, bookings = _read(processed_dir, DEMANDS_FILE), _read(processed_dir, BOOKINGS_FILE)
    payload: dict[str, Any] = {"data_available": demands is not None, "plan_area": plan_area, "planning_basis": PLANNING_BASIS,
                               "demand": None, "days": [], "bookings": None}
    if demands is not None:
        rows = _area(demands, plan_area)
        if not rows.empty:
            days = rows["scheduled_date"].astype(str)
            ready = rows["demand_input_status"] == READY_STATUS
            per_day = pd.DataFrame({"day": days, "ready": ready, "event": rows["exam_event_id"].astype(str)})
            counts = [{"date": day, "ready": int(group.loc[group["ready"], "event"].nunique()),
                       "not_ready": int(group.loc[~group["ready"], "event"].nunique())} for day, group in per_day.groupby("day")]
            payload["demand"] = {"first": days.min(), "last": days.max(), "source": "Ladok (deltagarantal)",
                                 "ready_events": int(rows.loc[ready, "exam_event_id"].nunique()),
                                 "not_ready_events": int(rows.loc[~ready, "exam_event_id"].nunique())}
            payload["days"] = counts
    if bookings is not None and "scheduled_date" in bookings:
        dates = bookings["scheduled_date"].dropna().astype(str)
        if not dates.empty:
            payload["bookings"] = {"first": dates.min(), "last": dates.max(), "source": "Lokalbokningar",
                                   "rows": int(len(bookings)),
                                   "note": "Bokningar visar vad som var lagt men ger ingen efterfrågan; de kan inte optimeras utan Ladokunderlag."}
    return payload


def period_report(processed_dir: Path, plan_area: str, first: date, last: date) -> dict[str, Any]:
    """The check of one period: counted exams, what is outside the data, and the reason when it cannot be planned."""
    coverage = coverage_payload(processed_dir, plan_area)
    report: dict[str, Any] = {"date_from": first.isoformat(), "date_to": last.isoformat(), "plan_area": plan_area, "coverage": coverage["demand"],
                              "planning_basis": PLANNING_BASIS, "ready_events": 0, "not_ready_events": 0, "planned_from": None,
                              "planned_to": None, "partial": False, "warnings": [], "error": None, "can_plan": False}
    if first > last:
        report["error"] = "Startdatum får inte vara senare än slutdatum."
        return report
    window = coverage["demand"]
    if window is None:
        report["error"] = f"Det finns inget förberett efterfrågeunderlag för {plan_area}. Förbered underlaget först."
        return report
    low, high = date.fromisoformat(window["first"]), date.fromisoformat(window["last"])
    if last < low or first > high:
        report["error"] = (f"Perioden ligger utanför efterfrågeunderlaget, som täcker {low.isoformat()}–{high.isoformat()}. "
                           "Utan deltagarantal går den inte att optimera.")
        return report
    inside_days = [row for row in coverage["days"] if first.isoformat() <= row["date"] <= last.isoformat()]
    report["ready_events"] = sum(row["ready"] for row in inside_days)
    report["not_ready_events"] = sum(row["not_ready"] for row in inside_days)
    report["planned_from"], report["planned_to"] = max(first, low).isoformat(), min(last, high).isoformat()
    report["partial"] = first < low or last > high
    if report["partial"]:
        report["warnings"].append(f"Delar av perioden saknar efterfrågeunderlag ({low.isoformat()}–{high.isoformat()} täcks). "
                                  f"Bara {report['planned_from']}–{report['planned_to']} kan planeras; resten är okänd, inte tom. "
                                  "Resultatet gäller då inte hela den valda perioden.")
    if report["not_ready_events"]:
        report["warnings"].append(f"{report['not_ready_events']} tentor i perioden saknar deltagarantal och ingår inte i planeringen.")
    if report["ready_events"] == 0:
        report["error"] = "Inga tentor med känt deltagarantal i den valda perioden."
        return report
    report["warnings"].append("Tentor nära periodens gränser kan inte flyttas utanför perioden, så de har mindre rörelsefrihet.")
    report["can_plan"] = True
    return report


def with_period(content: dict[str, Any], processed_dir: Path, request: PeriodRequest) -> dict[str, Any]:
    """A copy of the scenario planned for the chosen period (subset window and calendar), or `PeriodError`."""
    subset = content["subset"]
    if subset_kind(subset) != "rule" or subset.get("selection") != RULE_ALL_READY:
        raise PeriodError("Scenariot anger namngivna tentor och kan inte få ett periodval. Välj ett scenario med urvalsregeln 'alla klara tentor'.")
    report = period_report(processed_dir, str(subset.get("plan_area", "")), request.date_from, request.date_to)
    if not report["can_plan"]:
        raise PeriodError(str(report["error"]))
    if report["partial"] and not request.accept_partial:
        raise PeriodError(f"Perioden {request.date_from.isoformat()}–{request.date_to.isoformat()} täcks bara delvis av underlaget. "
                          f"Godkänn uttryckligen den kortare perioden {report['planned_from']}–{report['planned_to']} för att planera den.")
    first, last = report["planned_from"], report["planned_to"]
    merged = deepcopy(content)
    merged["subset"].update({"date_from": first, "date_to": last})
    # What was asked for and what is planned stay together in the run's frozen scenario, so a result can never read as the whole request.
    merged["period"] = {"requested_from": request.date_from.isoformat(), "requested_to": request.date_to.isoformat(),
                        "planned_from": first, "planned_to": last, "partial": bool(report["partial"]), "partial_accepted": bool(report["partial"])}
    merged.setdefault("parameters", {}).update({"calendar.start_date": first, "calendar.end_date": last})
    merged.setdefault("rationales", {}).update({"calendar.start_date": "Vald planeringsperiod i gränssnittet.",
                                                "calendar.end_date": "Vald planeringsperiod i gränssnittet."})
    return merged
