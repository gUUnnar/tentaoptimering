"""Hand-built joint-optimization artifacts with a hand-worked answer.

Nothing here is produced by the optimizer: the schedule, sessions, staffing and costs below were
worked out on paper, so the validator is checked against an independent answer.

Reference case (all times Monday 2026-01-12 unless stated, Tuesday is 2026-01-13):

    slots   s1 Mon 08:00   s2 Mon 14:00   s3 Tue 08:00   s4 Wed 08:00 (reference only, for the fixed exam)
    rooms   R1 100 seats, digital, cost 10 000   R2 60 seats, paper only, cost 6 000   (same building)
    ladder  <=50 -> 1 staff, <=100 -> 2, <=150 -> 3; preparation 30, closing 30, turnaround 30
    costs   pool 1 000 per staff, 100 per staffed room session

    A  50 participants, 4 h, original s1  -> s1 in R2        session (R2,s1) 50 -> 1 staff   ends 12:00
    B  50 participants, 4 h, digital, original s2 -> s1 in R1 session (R1,s1) 50 -> 1 staff   ends 12:00 (changed)
    E  40 participants, 2 h, original s2  -> s2 in R1        session (R1,s2) 40 -> 1 staff   ends 16:00
    C 120 participants (70+50), 3 h, original s3 -> s3 in R1 (70) and R2 (50)
                                                              (R1,s3) 70 -> 2 staff, (R2,s3) 50 -> 1 staff, ends 11:00
    D  30 participants, hemtenta (no room), fixed at s4

    staff windows [start-30, end+30): Monday R1/R2 s1 = 07:30-12:30 (2), s2 = 13:30-16:30 (1) -> Monday peak 2;
    Tuesday R1 s3 (2) + R2 s3 (1) = 3 -> pool 3
    costs   rooms 10 000 + 6 000 = 16 000; pool 3 x 1 000 = 3 000; sessions (1+1+1+2+1) x 100 = 600; total 19 600
    changed exams: B only (1)
    participants: 290 in total, 260 placed in rooms, 30 without room
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

INPUT_VERSION = "joint-optimization-input-v2"
RESULT_VERSION = "joint-optimization-result-v2"


def _param(parameter_id: str, value: Any, basis: str = "assumption", support: str = "implemented", changed: bool = False) -> dict[str, Any]:
    return {"parameter_id": parameter_id, "value": value, "basis": basis, "rationale": "handräknat fall",
            "engine_support": support, "changed_from_default": changed}


def _demand(demand_id: str, count: int | list[int], hours: int, original: str, area: str = "Uppsala", course: str | None = None,
            digital: str = "paper", requires_room: bool = True, movable: bool = True, day: str = "2026-01-12", start: int = 480,
            candidates: list[str] | None = None, basis: str = "single_activity") -> dict[str, Any]:
    counts = count if isinstance(count, list) else [count]
    return {
        "exam_demand_id": demand_id,
        "participant_groups": [
            {"group_id": f"{demand_id}-g{index}", "participant_count": value, "source_activity_ids": [f"{demand_id}-a{index}"],
             "count_basis": "registered_count"} for index, value in enumerate(counts, start=1)
        ],
        "duration_minutes": hours * 60, "plan_area": area,
        "candidate_slot_ids": candidates if candidates is not None else (["s1", "s2", "s3"] if movable else [original]),
        "original_slot_id": original, "requires_room": requires_room, "course_code": course or f"K-{demand_id}",
        "conflict_group_ids": [f"course:{course or 'K-' + demand_id}"], "digital_requirement": digital, "max_rooms": 8,
        "allow_split_across_buildings": False, "original_date": day, "original_start_minute": start, "movable": movable,
        "participant_group_basis": basis, "digital_requirement_basis": "observed_ja" if digital == "e_exam" else "observed_nej",
    }


def reference_problem() -> dict[str, Any]:
    return {
        "schema_version": INPUT_VERSION, "problem_id": "hand-case", "dataset_hash": "hand",
        "slots": [
            {"slot_id": "s1", "scheduled_date": "2026-01-12", "pass_id": "08:00", "start_minute": 480, "latest_end_minute": 1200, "reference_only": False},
            {"slot_id": "s2", "scheduled_date": "2026-01-12", "pass_id": "14:00", "start_minute": 840, "latest_end_minute": 1200, "reference_only": False},
            {"slot_id": "s3", "scheduled_date": "2026-01-13", "pass_id": "08:00", "start_minute": 480, "latest_end_minute": 1200, "reference_only": False},
            {"slot_id": "s4", "scheduled_date": "2026-01-14", "pass_id": "08:00", "start_minute": 480, "latest_end_minute": 1200, "reference_only": True},
        ],
        "demands": [
            _demand("A", 50, 4, "s1"),
            _demand("B", 50, 4, "s2", digital="e_exam", start=840),
            _demand("C", [70, 50], 3, "s3", day="2026-01-13", basis="assumed_disjoint_groups_sum"),
            _demand("D", 30, 3, "s4", requires_room=False, movable=False, day="2026-01-14"),
            _demand("E", 40, 2, "s2", start=840),
        ],
        "rooms": [
            {"room_id": "R1", "building_id": "b1", "plan_area": "Uppsala", "capacity": 100, "annual_fixed_cost_ore": 10000,
             "external_session_cost_ore": 0, "digital_capabilities": ["paper", "e_exam"], "available_slot_ids": None, "digital_support_basis": "all_places"},
            {"room_id": "R2", "building_id": "b1", "plan_area": "Uppsala", "capacity": 60, "annual_fixed_cost_ore": 6000,
             "external_session_cost_ore": 0, "digital_capabilities": ["paper"], "available_slot_ids": None, "digital_support_basis": "unknown"},
        ],
        "staffing": {"ladder": [{"max_participants": 50, "required_staff": 1}, {"max_participants": 100, "required_staff": 2},
                                {"max_participants": 150, "required_staff": 3}],
                     "annual_cost_ore_per_staff": 1000, "cost_ore_per_staff_session": 100, "preparation_minutes": 30, "closing_minutes": 30},
        "solver": {"time_limit_seconds": 5.0, "random_seed": 1, "num_workers": 1, "deterministic": False},
        "parameters": [
            _param("window.earlier_days", 1), _param("window.later_days", 1), _param("calendar.weekdays", [1, 2, 3, 4, 5]),
            _param("calendar.blocked_ranges", []), _param("calendar.start_times", ["08:00", "14:00"]),
            _param("calendar.earliest_start_time", "08:00"), _param("calendar.latest_end_time", "20:00"),
            _param("calendar.start_date", ""), _param("calendar.end_date", "2026-01-13"),
            _param("staffing.ladder", [], "assumption"), _param("cost.room_annual_per_seat_ore", 100),
            _param("rules.student_conflicts", False, "source_data", "contract_only"),
        ],
        "scope": {"source_activities_total": 20, "included_source_activities": 13, "unresolved_source_activities": 7,
                  "excluded_source_activities": 0, "modeled_exam_demands": 5, "modeled_participants": 290},
        "turnaround_minutes": 30,
    }


def _schedule(demand: str, slot: str, original: str, day: str, start: int, count: int, room: bool = True) -> dict[str, Any]:
    return {"exam_demand_id": demand, "slot_id": slot, "original_slot_id": original, "original_date": day,
            "original_start_minute": start, "requires_room": room, "participants": count}


def _session(room: str, slot: str, demands: list[str], count: int, staff: int, available_again: int) -> dict[str, Any]:
    return {"room_id": room, "building_id": "b1", "slot_id": slot, "exam_demand_ids": demands, "participants": count,
            "required_staff": staff, "available_again_minute": available_again}


def reference_result() -> dict[str, Any]:
    return {
        "schema_version": RESULT_VERSION, "problem_id": "hand-case",
        "solver": {"outcome": "optimal", "raw_status": "optimal", "objective_value_ore": 19600, "best_objective_bound_ore": 19600,
                   "relative_gap": 0.0, "wall_time_seconds": 0.1, "change_preference_status": "optimal_at_economic_optimum"},
        "costs": {"annual_room_cost_ore": 16000, "external_room_session_cost_ore": 0, "annual_staff_pool_cost_ore": 3000,
                  "staff_session_cost_ore": 600, "comparable_total_cost_ore": 19600},
        "coverage": {"exam_demands_total": 5, "exam_demands_scheduled": 5, "participants_total": 290,
                     "participants_assigned_to_rooms": 260, "non_room_participants_scheduled": 30, "technical_placement_complete": True},
        "staff_pool_size": 3, "changed_exam_demands": 1,
        "assignments": [
            {"exam_demand_id": "A", "slot_id": "s1", "room_id": "R2", "participants": 50},
            {"exam_demand_id": "B", "slot_id": "s1", "room_id": "R1", "participants": 50},
            {"exam_demand_id": "C", "slot_id": "s3", "room_id": "R1", "participants": 70},
            {"exam_demand_id": "C", "slot_id": "s3", "room_id": "R2", "participants": 50},
            {"exam_demand_id": "E", "slot_id": "s2", "room_id": "R1", "participants": 40},
        ],
        "room_sessions": [
            _session("R1", "s1", ["B"], 50, 1, 750), _session("R2", "s1", ["A"], 50, 1, 750),
            _session("R1", "s2", ["E"], 40, 1, 990), _session("R1", "s3", ["C"], 70, 2, 690), _session("R2", "s3", ["C"], 50, 1, 690),
        ],
        "schedule": [
            _schedule("A", "s1", "s1", "2026-01-12", 480, 50), _schedule("B", "s1", "s2", "2026-01-12", 840, 50),
            _schedule("C", "s3", "s3", "2026-01-13", 480, 120), _schedule("D", "s4", "s4", "2026-01-14", 480, 30, False),
            _schedule("E", "s2", "s2", "2026-01-12", 840, 40),
        ],
        "limitations": ["7 källaktiviteter är oavgjorda utanför den modellerade omfattningen."],
        "verification": {"independent_validation": "not_performed"},
    }


def pair_case(preparation: int, closing: int, pool: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Two 2-hour exams of 30 participants in different rooms, 08:00 and 10:30, no other staff.

    The first session ends 10:00 and the second starts 10:30. Their staff windows are
    [08:00-prep, 10:00+closing) and [10:30-prep, ...): they touch at prep = closing = 15 (needing 1 in the pool)
    and overlap by one minute at 16 (needing 2).
    """
    problem = reference_problem()
    problem["slots"] = [
        {"slot_id": "a", "scheduled_date": "2026-01-12", "pass_id": "08:00", "start_minute": 480, "latest_end_minute": 1200, "reference_only": False},
        {"slot_id": "b", "scheduled_date": "2026-01-12", "pass_id": "10:30", "start_minute": 630, "latest_end_minute": 1200, "reference_only": False},
    ]
    problem["demands"] = [
        _demand("P", 30, 2, "a", candidates=["a", "b"]), _demand("Q", 30, 2, "b", start=630, candidates=["a", "b"]),
    ]
    problem["parameters"] = [
        item for item in problem["parameters"] if item["parameter_id"] not in ("calendar.start_times", "calendar.end_date")
    ] + [_param("calendar.start_times", ["08:00", "10:30"]), _param("calendar.end_date", "2026-01-12")]
    problem["staffing"]["preparation_minutes"], problem["staffing"]["closing_minutes"] = preparation, closing
    problem["staffing"]["cost_ore_per_staff_session"] = 0
    problem["scope"].update(modeled_exam_demands=2, modeled_participants=60, unresolved_source_activities=0)
    result = reference_result()
    result["assignments"] = [
        {"exam_demand_id": "P", "slot_id": "a", "room_id": "R1", "participants": 30},
        {"exam_demand_id": "Q", "slot_id": "b", "room_id": "R2", "participants": 30},
    ]
    result["room_sessions"] = [_session("R1", "a", ["P"], 30, 1, 630), _session("R2", "b", ["Q"], 30, 1, 780)]
    result["schedule"] = [_schedule("P", "a", "a", "2026-01-12", 480, 30), _schedule("Q", "b", "b", "2026-01-12", 630, 30)]
    total = 16000 + 1000 * pool
    result["costs"].update(annual_staff_pool_cost_ore=1000 * pool, staff_session_cost_ore=0, comparable_total_cost_ore=total)
    result["solver"].update(objective_value_ore=total, best_objective_bound_ore=total)
    result["coverage"].update(exam_demands_total=2, exam_demands_scheduled=2, participants_total=60,
                              participants_assigned_to_rooms=60, non_room_participants_scheduled=0)
    result["staff_pool_size"], result["changed_exam_demands"], result["limitations"] = pool, 0, []
    return problem, result


def write_run(directory: Path, problem: dict[str, Any], result: dict[str, Any], manifest: bool = True) -> Path:
    """Save the artifacts in the same file names and manifest format as a real run."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "joint_input.json").write_text(json.dumps(problem, ensure_ascii=False, indent=2), encoding="utf-8")
    (directory / "joint_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if manifest:
        digest = lambda name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        (directory / "joint_manifest.json").write_text(json.dumps({
            "input_sha256": digest("joint_input.json"), "result_sha256": digest("joint_result.json"),
            "config_sha256": "none", "catalog_sha256": "none",
        }), encoding="utf-8")
    return directory


def copy_case() -> tuple[dict[str, Any], dict[str, Any]]:
    return deepcopy(reference_problem()), deepcopy(reference_result())
