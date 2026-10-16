"""Rules for fixed bookings, paid staff time and the resource data a run rests on.

All of it is recomputed from the saved input and result. The paid-time rules follow the definition in the saved input:
one paid pass per staff position of a session, at least the shortest paid pass, plus the room's travel minutes.
"""

from __future__ import annotations

from .context import Context
from .derive import build_sessions, paid_passes, staff_by_session
from .report import BUSINESS, FAIL, NOT_APPLICABLE, NOT_EVALUATED, PASS, TECHNICAL, RuleResult, rule

_TECHNICAL = ("reservations_respected", "paid_time_recomputed")


def resource_rules(ctx: Context) -> list[RuleResult]:
    results = [_reservations(ctx), _paid_time(ctx)] if ctx.has_solution else [
        rule(name, TECHNICAL, NOT_APPLICABLE, "Resultatet innehåller ingen lösning att validera.") for name in _TECHNICAL]
    return results + [_reservation_coverage(ctx), _resource_basis(ctx)]


def _reservations(ctx: Context) -> RuleResult:
    usable = [item for item in ctx.reservations if item.room_id in ctx.rooms]
    if not usable:
        return rule("reservations_respected", TECHNICAL, NOT_APPLICABLE, "Inga fasta bokningar spärrar någon sal i modellen.", reference="krav: befintliga bokningar blockerar resurser")
    sessions = build_sessions(ctx)
    broken = []
    for item in usable:
        for session in sessions.values():
            if session.room_id != item.room_id or session.day != item.day:
                continue
            if not (session.end + ctx.turnaround <= item.start or item.end + ctx.turnaround <= session.start):
                broken.append(f"{session.room_id}@{session.slot_id} ({session.start}–{session.end}) mot fast bokning {item.reservation_id} ({item.start}–{item.end})")
    return rule("reservations_respected", TECHNICAL, FAIL if broken else PASS,
                "Ett salstillfälle överlappar en fast bokning eller saknar ställtid mot den." if broken
                else f"Inget salstillfälle överlappar någon av de {len(usable)} fasta bokningarna (ställtid {ctx.turnaround} minuter hålls).",
                broken, "krav: befintliga bokningar blockerar resurser")


def _paid_time(ctx: Context) -> RuleResult:
    sessions = build_sessions(ctx)
    staff = staff_by_session(ctx, sessions)
    passes = paid_passes(ctx, sessions, staff)
    expected = {"passes": len(passes), "paid_minutes": sum(item["paid"] for item in passes), "worked_minutes": sum(item["worked"] for item in passes),
                "minimum_top_up_minutes": sum(item["top_up"] for item in passes), "travel_minutes": sum(item["travel"] for item in passes)}
    summary = ctx.result.get("staffing_summary")
    if not isinstance(summary, dict) and not ctx.paid_minute_cost and not (ctx.result.get("costs") or {}).get("staff_paid_time_cost_ore"):
        return rule("paid_time_recomputed", TECHNICAL, NOT_APPLICABLE,
                    "Ingen betald personaltid är prissatt i körningen (kostnad per betald minut är 0) och ingen redovisas.", reference="krav: kostnad härleds ur betald tid")
    if not isinstance(summary, dict):
        return rule("paid_time_recomputed", TECHNICAL, NOT_EVALUATED,
                    "Resultatet redovisar ingen betald personaltid (äldre körning); den kan inte jämföras med omräkningen.", reference="krav: kostnad härleds ur betald tid")
    broken = [f"{name}: rapporterat {summary.get(name)}, beräknat {value}" for name, value in expected.items() if summary.get(name) != value]
    costs = ctx.result.get("costs") or {}
    cost = ctx.paid_minute_cost * expected["paid_minutes"]
    if costs.get("staff_paid_time_cost_ore", 0) != cost:
        broken.append(f"kostnaden för betald tid: rapporterat {costs.get('staff_paid_time_cost_ore', 0)}, beräknat {cost}")
    per_day: dict[str, int] = {}
    for item in passes:
        per_day[item["day"]] = per_day.get(item["day"], 0) + item["paid"]
    reported_days = {day: row.get("paid_minutes") for day, row in (summary.get("per_day") or {}).items()}
    if reported_days != per_day:
        broken.append("betalda minuter per dag stämmer inte med omräkningen")
    return rule("paid_time_recomputed", TECHNICAL, FAIL if broken else PASS,
                "Redovisad betald personaltid eller dess kostnad avviker från omräkningen ur placeringen." if broken
                else f"{expected['passes']} betalda pass och {expected['paid_minutes']} betalda minuter ({expected['paid_minutes'] / 60:.1f} timmar) räknas om ur placeringen "
                     f"(arbetad tid, kortaste pass, restid) och kostar {cost} öre.", broken, "krav: kostnad härleds ur betald tid")


def _reservation_coverage(ctx: Context) -> RuleResult:
    basis = (ctx.resource_basis or {}).get("reservations")
    if basis is None:
        return rule("reservations_coverage_verified", BUSINESS, NOT_EVALUATED,
                    "Körningen redovisar ingen grund för fasta bokningar (äldre körning); att bokningar utanför valda tentor inte blockerade något kan inte bedömas.",
                    reference="krav: fasta bokningar får inte ignoreras")
    if basis.get("status") == "ignored_by_parameter":
        return rule("reservations_coverage_verified", BUSINESS, NOT_EVALUATED,
                    "Fasta bokningar ignorerades enligt parametern; körningen är explorativ och kan placera tentor i upptagna salar.",
                    reference="krav: fasta bokningar får inte ignoreras")
    unknown = int(basis.get("unidentified_bookings", 0))
    return rule("reservations_coverage_verified", BUSINESS, NOT_EVALUATED,
                f"{basis.get('blocking', 0)} fasta bokningar spärrar salar. {unknown} bokningar i perioden saknar identifierad sal och spärrar ingenting; deras upptagenhet är okänd. "
                "Fullständigheten är inte oberoende kontrollerad.", reference="krav: fasta bokningar får inte ignoreras")


def _resource_basis(ctx: Context) -> RuleResult:
    basis = ctx.resource_basis or {}
    pack = basis.get("pack")
    if not pack:
        return rule("resource_data_verified", BUSINESS, NOT_EVALUATED,
                    "Ingen resursdata är vald: lokalkostnaden är en kostnad per plats (proxy) och externhyror finns inte. Kostnaden är inte avtalsgrundad.",
                    reference="krav: kostnadsantaganden är verifierade")
    origins = ", ".join(pack.get("origins") or [pack.get("pack_origin", "okänt")])
    proxies = [item["room_id"] for item in basis.get("rooms", ()) if item.get("kind") == "internal" and item.get("cost_origin") == "parameter_proxy"]
    return rule("resource_data_verified", BUSINESS, NOT_EVALUATED,
                f"Resursdata ”{pack.get('pack_id')}” med ursprung {origins}. Simulerade eller antagna uppgifter är aldrig verifierade; en observerad uppgift räknas inte som "
                f"verifierad utan oberoende avstämning. {len(proxies)} salar saknar kostnad i resursdatan och prissätts per plats.",
                proxies, "krav: kostnadsantaganden är verifierade")
