"""What the engine prefers among placements of equal cost (the second, lexicographic goal after the economic one).

The economic goal is always first: nothing here can make a plan more expensive. Among plans of the same cost the
engine takes the one with the smallest total *penalty*, and the penalty of an exam on a candidate occasion is

* `fewest_changes`: 0 at the booked occasion, 1 at any other (the original behaviour);
* `wish_priority`: 2 × the rank of the occasion's date among the business's wishes (0 requested date, 1 reserve date 1,
  2 reserve date 2, 3 any other date) plus 1 if it is not the booked occasion. The wish order always dominates the
  tie-break on the booked occasion, and the booked occasion still breaks a tie between occasions of the same rank.

An exam without wishes is treated as in `fewest_changes`. Weights are what the three places that optimise (the whole
model, the relaxation and the day sub-problems) share, so the preference means the same everywhere.
"""

from __future__ import annotations

from .joint_contract import ExamDemand, JointOptimizationInput

FEWEST_CHANGES, WISH_PRIORITY = "fewest_changes", "wish_priority"
PREFERENCES = (FEWEST_CHANGES, WISH_PRIORITY)
OTHER_RANK = 3


def wish_rank(demand: ExamDemand, iso_date: str) -> int:
    """0, 1 or 2 for the requested date or a reserve date, 3 for any other date."""
    for rank, wished in enumerate(demand.wish_dates):
        if wished is not None and wished == iso_date:
            return rank
    return OTHER_RANK


def slot_penalty(problem: JointOptimizationInput, demand: ExamDemand, slot_id: str, slot_date: str) -> int:
    changed = int(demand.original_slot_id is not None and slot_id != demand.original_slot_id)
    if problem.preference == WISH_PRIORITY and any(item is not None for item in demand.wish_dates):
        return 2 * wish_rank(demand, slot_date) + changed
    return changed


def penalty_weights(problem: JointOptimizationInput, demands: tuple[ExamDemand, ...] | None = None) -> dict[tuple[str, str], int]:
    """(exam, slot) -> penalty, only for exams where the candidates differ in penalty (the others add a constant).

    Under `fewest_changes` this is the old rule: an exam counts only if its booked occasion is one of its candidates.
    """
    slot_date = {slot.slot_id: slot.scheduled_date.isoformat() for slot in problem.slots}
    weights: dict[tuple[str, str], int] = {}
    for demand in problem.demands if demands is None else demands:
        if problem.preference != WISH_PRIORITY and (demand.original_slot_id is None or demand.original_slot_id not in demand.candidate_slot_ids):
            continue
        penalties = {slot_id: slot_penalty(problem, demand, slot_id, slot_date[slot_id]) for slot_id in demand.candidate_slot_ids}
        if len(set(penalties.values())) > 1:
            weights.update({(demand.exam_demand_id, slot_id): value for slot_id, value in penalties.items() if value})
    return weights


def max_penalty(weights: dict[tuple[str, str], int]) -> int:
    """An upper bound on the total penalty, for scaling the economic goal above it."""
    best: dict[str, int] = {}
    for (exam, _), value in weights.items():
        best[exam] = max(best.get(exam, 0), value)
    return sum(best.values())


def has_preference(problem: JointOptimizationInput) -> bool:
    """Whether any exam can avoid a penalty: its booked occasion is a candidate, or (wish priority) it has wishes."""
    return any(
        (demand.original_slot_id is not None and demand.original_slot_id in demand.candidate_slot_ids)
        or (problem.preference == WISH_PRIORITY and any(item is not None for item in demand.wish_dates))
        for demand in problem.demands
    )
