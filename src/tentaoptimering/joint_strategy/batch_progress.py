"""Progress reporting for a batch of exact day checks (observation only).

A batch is reported when it starts, after each of its checks (a `day` event, then a `batch` event with
the counts so far) and once more when it is complete. The counts are updated under a lock together with the
events, so the `done` counter never runs backwards in the event order even though the checks finish on
different threads. Nothing here influences the checks: with no sink every method returns at once.
"""

from __future__ import annotations

from collections import Counter
from functools import wraps
import logging
import threading
from typing import TYPE_CHECKING, Any, Callable, Sequence

from ..joint_progress import ProgressSink, emit

if TYPE_CHECKING:
    from .verification import Outcome, Request


LOG = logging.getLogger(__name__)


def _harmless(method: Callable[..., None]) -> Callable[..., None]:
    """A reporting error is logged and dropped: it must never reach a check running on a solver thread."""
    @wraps(method)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            method(*args, **kwargs)
        except Exception:
            LOG.warning("batch progress could not be reported", exc_info=True)
    return wrapper


class BatchReporter:
    def __init__(self, progress: ProgressSink | None, kind: str, total: int, parallel: int, workers: int) -> None:
        self._progress = progress
        self._lock = threading.Lock()
        self._fields = {"kind": kind, "total": total, "parallel": parallel, "workers_per_check": workers}
        self._done = 0
        self._statuses: Counter[str] = Counter()
        if progress is not None:
            self._start()

    @_harmless
    def _start(self) -> None:
        self._batch(0, Counter())

    @_harmless
    def checked(self, request: "Request", outcome: "Outcome", elapsed: float) -> None:
        """One check of the batch has finished (called from the thread that ran it)."""
        if self._progress is None:
            return
        with self._lock:
            self._done += 1
            self._statuses[outcome[0]] += 1
            self._day(request, outcome[0], elapsed)
            self._batch(self._done, self._statuses)

    @_harmless
    def repeated(self, request: "Request", outcome: "Outcome", elapsed: float) -> None:
        """A check that timed out with few workers was repeated with all threads; its new status replaces the old."""
        if self._progress is not None:
            with self._lock:
                self._day(request, outcome[0], elapsed)

    @_harmless
    def finish(self, statuses: Sequence[str]) -> None:
        """The final counts of the batch, after any repeated checks."""
        if self._progress is not None:
            with self._lock:
                self._batch(len(statuses), Counter(statuses))

    def _day(self, request: "Request", status: str, elapsed: float) -> None:
        extra = {"block": [day.isoformat() for day in sorted(request.block)]} if len(request.block) > 1 else {}
        emit(self._progress, "day", date=min(request.block).isoformat(), kind=request.kind, status=status,
             seconds=round(elapsed, 3), **extra)

    def _batch(self, done: int, statuses: Counter[str]) -> None:
        emit(self._progress, "batch", **self._fields, done=done, statuses=dict(statuses))
