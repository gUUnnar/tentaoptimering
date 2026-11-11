"""Swedish wording of the moves that a repair suggestion can contain (`joint_repair`)."""

from __future__ import annotations

WEEKDAYS = {1: "måndag", 2: "tisdag", 3: "onsdag", 4: "torsdag", 5: "fredag", 6: "lördag", 7: "söndag"}
EXPLORATIVE = "Resultatet blir explorativt (en egen körning, C): fasta bokningar som tas bort spärrar ingenting, så det visar inte att salen är ledig i verkligheten."
GROUPS = {
    "reservations.action_no_count": "Tentor utan deltagarantal",
    "reservations.action_outside_selection": "Tentor utanför valt urval",
    "reservations.action_not_in_ladok": "Bokningar utan tentamen i underlaget",
}


def weekday_label(day: int) -> str:
    return f"Tillåt {WEEKDAYS[day]} i kalendern"


def start_time_label(clock: str) -> str:
    return f"Tillåt starttiden {clock}"


def calendar_label(side: str, day: str) -> str:
    return f"Flytta kalenderns {'start' if side == 'start' else 'slut'} till {day}"


def window_label(side: str, days: int) -> str:
    return f"Låt tentor flyttas upp till {days} {'dag' if days == 1 else 'dagar'} {'tidigare' if side == 'earlier' else 'senare'}"


POLICY_LABEL = "Låt tentor flyttas både till önskade datum och till fönstret kring bokat datum"


def remove_group_label(parameter: str, bookings: int) -> str:
    return f"Ta bort fasta bokningar: {GROUPS.get(parameter, parameter)} ({bookings} st)"


NO_BLOCK_LABEL = "Ta bort alla fasta bokningar (ingen spärr)"
