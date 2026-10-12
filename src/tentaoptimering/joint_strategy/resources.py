"""Shared compute budget and ordered parallel execution for the exact day checks.

The budget has one number of CP-SAT worker threads and one memory ceiling for the whole run. A batch
of independent checks divides the threads between the checks that run at the same time, so that
`parallel checks x workers per check` never exceeds the budget (eight parallel CP-SAT instances do
not each get eight threads).

The division depends only on the batch (its size and the estimated memory), never on which check
finishes first. Results are returned in request order. Hence the content and order of a result
do not depend on completion order. What stays timing dependent is only whether a check hits its
time limit, exactly as in a sequential run.

`CancelToken` stops a run: it makes every running CP-SAT solver return and keeps new ones from starting.
"""

from __future__ import annotations

import ctypes
from concurrent.futures import FIRST_EXCEPTION, Future, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass, replace
import os
import threading
import time
from typing import Any, Callable, Iterator, Sequence, TypeVar

from ortools.sat.python import cp_model

from ..joint_contract import SolverSettings

T = TypeVar("T")

DEFAULT_MEMORY_MB = 4096
MEMORY_SHARE = 0.5          # of the physical memory that is free when the run starts
BASE_TASK_MB = 32.0         # one day check: model, solver and Python objects
PAIR_TASK_MB = 0.02         # per (exam, candidate slot, room) triple in the check


@dataclass(frozen=True)
class ExecutionBudget:
    """CPU threads and memory for one run. `threads` 0 means the scenario's own worker count."""

    threads: int = 0
    memory_mb: int | None = None
    parallel_day_checks: bool = True
    workers_per_check: int = 0      # 0: as many parallel checks as threads allow, each with the rest

    def resolve(self, settings: SolverSettings) -> "ExecutionBudget":
        threads = self.threads if self.threads > 0 else settings.num_workers
        memory = self.memory_mb if self.memory_mb is not None else default_memory_mb()
        return replace(self, threads=max(1, threads), memory_mb=max(1, memory))

    def settings(self, base: SolverSettings, workers: int | None = None) -> SolverSettings:
        return replace(base, num_workers=max(1, workers if workers is not None else self.threads))

    def describe(self) -> dict[str, Any]:
        return {"threads": self.threads, "memory_mb": self.memory_mb, "parallel_day_checks": self.parallel_day_checks,
                "workers_per_check": self.workers_per_check}


def default_memory_mb() -> int:
    """Half of the free physical memory; a fixed fallback if the system cannot tell."""
    free = _free_memory_bytes()
    return int(free / 2**20 * MEMORY_SHARE) if free else DEFAULT_MEMORY_MB


def _free_memory_bytes() -> int | None:
    try:
        if os.name == "nt":
            class Status(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("available", ctypes.c_ulonglong), ("page_total", ctypes.c_ulonglong),
                            ("page_available", ctypes.c_ulonglong), ("virtual_total", ctypes.c_ulonglong),
                            ("virtual_available", ctypes.c_ulonglong), ("extended", ctypes.c_ulonglong)]
            status = Status()
            status.length = ctypes.sizeof(Status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
                return int(status.available)
            return None
        return int(os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, ValueError):
        return None


def task_memory_mb(pairs: int) -> float:
    """Estimated memory of one day check from the size of its model."""
    return BASE_TASK_MB + PAIR_TASK_MB * pairs


def plan_batch(tasks: int, task_mb: float, budget: ExecutionBudget) -> tuple[int, int]:
    """(checks run at the same time, CP-SAT workers per check) for a batch of independent checks.

    The estimate for the largest check in the batch bounds the number of simultaneous checks. A
    batch of one, or a run with parallel checks switched off, uses all threads for one check.
    """
    if not budget.parallel_day_checks or tasks <= 1:
        return 1, budget.threads
    parallel = min(tasks, budget.threads)
    if budget.workers_per_check > 0:
        parallel = min(tasks, max(1, budget.threads // budget.workers_per_check))
    if budget.memory_mb is not None:
        parallel = min(parallel, max(1, int(budget.memory_mb // max(1.0, task_mb))))
    return parallel, max(1, budget.threads // parallel)


class CancelToken:
    """Cooperative stop for a whole run, usable from any thread."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._solvers: set[cp_model.CpSolver] = set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        with self._lock:
            self._event.set()
            running = list(self._solvers)
        for solver in running:
            solver.StopSearch()
        if running:
            # A solver registered but not yet inside Solve() ignores StopSearch; keep asking briefly.
            threading.Thread(target=self._keep_stopping, daemon=True).start()

    def _keep_stopping(self) -> None:
        for _ in range(100):
            with self._lock:
                running = list(self._solvers)
            if not running:
                return
            for solver in running:
                solver.StopSearch()
            time.sleep(0.05)

    @contextmanager
    def watch(self, solver: cp_model.CpSolver) -> Iterator[None]:
        with self._lock:
            self._solvers.add(solver)
        try:
            yield
        finally:
            with self._lock:
                self._solvers.discard(solver)


def solve_cancellable(solver: cp_model.CpSolver, model: cp_model.CpModel, cancel: CancelToken | None) -> int:
    """`solver.Solve(model)` that returns UNKNOWN at once if the run is cancelled, and stops when it is."""
    if cancel is None:
        return solver.Solve(model)
    if cancel.cancelled:
        return cp_model.UNKNOWN
    with cancel.watch(solver):
        return solver.Solve(model)


def run_ordered(calls: Sequence[Callable[[], T]], parallel: int, cancel: CancelToken | None = None) -> list[T]:
    """Run independent calls and return their results in call order.

    With `parallel` 1 the calls run one after the other in this thread. If a call raises, the others are
    stopped and the error of the lowest-numbered failing call is raised, whichever failed first in time.
    An interrupt in the calling thread stops all calls before it propagates.
    """
    if parallel <= 1 or len(calls) <= 1:
        return [call() for call in calls]
    pool = ThreadPoolExecutor(max_workers=min(parallel, len(calls)), thread_name_prefix="daycheck")
    futures: list[Future[T]] = []
    try:
        futures = [pool.submit(call) for call in calls]
        wait(futures, return_when=FIRST_EXCEPTION)
        failed = any(future.done() and not future.cancelled() and future.exception() for future in futures)
        if failed:
            _stop(futures, cancel)
        else:
            wait(futures)
    except BaseException:
        _stop(futures, cancel)
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    for future in futures:
        if not future.cancelled() and future.exception() is not None:
            raise future.exception()  # type: ignore[misc]
    return [future.result() for future in futures]


def _stop(futures: list[Future[Any]], cancel: CancelToken | None) -> None:
    if cancel is not None:
        cancel.cancel()
    for future in futures:
        future.cancel()
    wait(futures)
