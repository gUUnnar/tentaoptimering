"""Time the same joint engine on a day, a week and a larger period chosen the way the interface does (`period` in the run request).

Runs in a throw-away storage folder with a copy of `data/processed`, so no saved runs of the user are touched. Each case goes
through `start_joint_run` (validation, snapshot, engine, independent validation) and is read back with `run_summary`; the
times are the ones the result view shows (`first_solution_seconds`, `wall_time_seconds`) plus the elapsed time of the whole job.

    python tools/measure_period_runs.py [--cases day,week,month,all] [--time-limit 120]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from tentaoptimering.app_storage import AppStorage  # noqa: E402
from tentaoptimering.job_manager import LocalJobManager  # noqa: E402
from tentaoptimering.joint_api import JointRunRequest, run_summary, start_joint_run  # noqa: E402
from tentaoptimering.joint_period import PeriodRequest  # noqa: E402

CASES = {
    "day": ("2026-02-09", "2026-02-09"),
    "week": ("2026-02-09", "2026-02-15"),
    "month": ("2026-02-01", "2026-02-28"),
    "all": ("2026-01-12", "2026-03-31"),
}
SCENARIO = "joint_underlay_period"


def measure(storage: AppStorage, jobs: LocalJobManager, name: str, period: tuple[str, str], time_limit: float) -> dict:
    request = JointRunRequest(scenario=SCENARIO, warm_start="none", period=PeriodRequest(date_from=period[0], date_to=period[1]),
                              parameters={"solver.time_limit_seconds": time_limit})
    started = time.perf_counter()
    job = start_joint_run(jobs, storage, request)
    while jobs.public(job["job_id"])["status"] in ("queued", "running"):
        time.sleep(0.2)
    elapsed = time.perf_counter() - started
    public = jobs.public(job["job_id"])
    if public["status"] != "completed":
        return {"case": name, "period": period, "status": public["status"], "error": public.get("error"), "job_seconds": round(elapsed, 1)}
    summary = run_summary(storage, public["result"]["run_id"])
    return {"case": name, "period": period, "status": "completed", "exams": summary["exams_total"], "solver_outcome": summary["solver_outcome"],
            "verified": summary["has_verified_solution"], "technical_validation": summary["verdicts"]["technical_validation"],
            "business_verification": summary["verdicts"]["business_verification"], "cost_ore": summary["cost_ore"],
            "gap_relative": summary["gap_relative"], "first_solution_seconds": summary["first_solution_seconds"],
            "first_solution_basis": summary["first_solution_basis"], "solver_wall_seconds": summary["wall_time_seconds"],
            "job_seconds": round(elapsed, 1), "time_limit_seconds": time_limit}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", default="day,week,month")
    parser.add_argument("--time-limit", type=float, default=120.0)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        storage = AppStorage(Path(folder))
        shutil.copytree(REPO_ROOT / "data" / "processed", storage.processed_dir, dirs_exist_ok=True)
        jobs = LocalJobManager()
        for name in args.cases.split(","):
            print(json.dumps(measure(storage, jobs, name, CASES[name], args.time_limit), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
