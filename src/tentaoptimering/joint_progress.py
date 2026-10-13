"""Observation of a joint optimisation run: an ordered, thread-safe stream of events.

The solver reports what it does (phases, day checks, better solutions, bounds, resources) to an optional
`ProgressSink`. The events are only observations: they never influence a decision, a cost or a result, and a
failure to record one is swallowed (and logged) so it can never reach the solver. Without a sink (`None`)
nothing is recorded and nothing is paid for.

Every event is a flat dict `{"seq", "t", "type", ...fields}`:

* `seq` starts at 1 and is assigned under the sink's lock, so events from parallel threads have one
  stable order that is also the order in the file;
* `t` is seconds since the sink was created;
* the fields per type are the contract with the interface (see `EVENT_TYPES`).

With a file, each event is written as one JSON line and flushed at once, so a run that is cut off still
leaves a readable log (`joint_events.jsonl` in the run directory). A file may be attached later, when the
run directory exists: the events recorded so far are then written first, in order.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any, Iterator, TextIO

LOG = logging.getLogger(__name__)

EVENTS_FILE = "joint_events.jsonl"

PHASES = ("warm_start_check", "relaxation", "day_checks", "repair", "history", "finalize")

# type -> fields besides seq, t and type. Documentation and a check in the tests; emit() does not enforce it.
EVENT_TYPES: dict[str, tuple[str, ...]] = {
    "phase": ("name", "state"),
    "batch": ("kind", "total", "done", "parallel", "workers_per_check", "statuses"),
    "day_started": ("date", "kind"),
    "day": ("date", "kind", "status", "seconds"),
    "incumbent": ("cost_ore", "source", "changed_exams"),
    "bound": ("lower_ore", "round"),
    "warm_start": ("decision", "explanation", "source_run_id"),
    "resources": ("threads", "memory_mb", "parallel_checks", "workers_per_check"),
    "finished": ("outcome", "cost_ore", "bound_ore", "cancelled"),
}


class ProgressSink:
    """Collects events in memory and, if a path is given or attached, line by line in a JSONL file."""

    def __init__(self, path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []
        self._started = time.perf_counter()
        self._file: TextIO | None = None
        self._path: Path | None = None
        self._deferred_types: set[str] = set()
        self._deferred: list[tuple[str, dict[str, Any]]] = []
        self.run_id: str | None = None  # set by the run that owns the sink, once its directory exists
        if path is not None:
            self.attach(path)

    def emit(self, type: str, **fields: Any) -> None:  # noqa: A002 - the contract names the field `type`
        """Record one event. Never raises."""
        try:
            with self._lock:
                if type in self._deferred_types:
                    self._deferred.append((type, fields))
                else:
                    self._append(type, fields)
        except Exception:  # an observation must never disturb the solver
            LOG.warning("progress event %r could not be recorded", type, exc_info=True)

    def defer(self, *types: str) -> None:
        """Hold back events of these types until `release()`.

        A run uses it to make `finished` the last event: the solver ends before the artifacts are saved and
        validated, and a reader that acts on `finished` (fetching the summary) needs them to exist.
        """
        with self._lock:
            self._deferred_types.update(types)

    def release(self) -> None:
        """Record the held-back events, in the order they came, and stop holding back. Never raises."""
        try:
            with self._lock:
                held, self._deferred = self._deferred, []
                self._deferred_types.clear()
                for type, fields in held:  # noqa: A001
                    self._append(type, fields)
        except Exception:
            LOG.warning("held-back progress events could not be recorded", exc_info=True)

    def discard(self, *types: str) -> None:
        """Drop held-back events of these types (all held-back events if none are named) and stop holding back."""
        with self._lock:
            self._deferred = [item for item in self._deferred if types and item[0] not in types]
            self._deferred_types.clear()

    def elapsed(self) -> float:
        """Seconds since the sink was created, i.e. since the run was queued."""
        return round(time.perf_counter() - self._started, 3)

    def _append(self, type: str, fields: dict[str, Any]) -> None:  # noqa: A002
        event = {"seq": len(self._events) + 1, "t": round(time.perf_counter() - self._started, 3), "type": type, **fields}
        self._events.append(event)
        self._write(event)

    def attach(self, path: Path) -> None:
        """Start writing to `path`; the events so far are written first. Never raises."""
        try:
            with self._lock:
                self.close_file()
                self._path = Path(path)
                self._file = self._path.open("w", encoding="utf-8")
                for event in self._events:
                    self._write(event)
        except Exception:
            self._file = None
            LOG.warning("progress file %s could not be opened", path, exc_info=True)

    def events(self, after: int = 0) -> list[dict[str, Any]]:
        """The events with `seq` greater than `after`, in order (copies)."""
        with self._lock:
            return [dict(event) for event in self._events[max(0, int(after)):]]

    @property
    def last_seq(self) -> int:
        with self._lock:
            return len(self._events)

    def has(self, type: str) -> bool:  # noqa: A002
        """Whether an event of this type was recorded or is being held back."""
        with self._lock:
            return any(event["type"] == type for event in self._events) or any(held == type for held, _ in self._deferred)

    def close(self) -> None:
        with self._lock:
            self.close_file()

    def close_file(self) -> None:
        """Close the file (the caller holds the lock). Never raises."""
        handle, self._file = self._file, None
        if handle is not None:
            try:
                handle.close()
            except Exception:
                LOG.warning("progress file could not be closed", exc_info=True)

    def _write(self, event: dict[str, Any]) -> None:
        if self._file is None:
            return
        try:
            self._file.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            self._file.flush()
        except Exception:
            LOG.warning("progress file %s could not be written; file logging is switched off", self._path, exc_info=True)
            self.close_file()


def emit(progress: ProgressSink | None, type: str, **fields: Any) -> None:  # noqa: A002
    """`progress.emit(...)` that costs nothing without a sink and never raises, whatever sink it is given."""
    if progress is not None:
        try:
            progress.emit(type, **fields)
        except Exception:
            LOG.warning("progress event %r could not be recorded", type, exc_info=True)


@contextmanager
def phase(progress: ProgressSink | None, name: str) -> Iterator[None]:
    """Report a phase as started and, however it ends, as finished."""
    emit(progress, "phase", name=name, state="started")
    try:
        yield
    finally:
        emit(progress, "phase", name=name, state="finished")


def finished_event(progress: ProgressSink | None, result: Any, cancelled: bool = False) -> Any:
    """Report the end of a solve from its result; returns the result unchanged. Reported once per sink."""
    if progress is not None:
        try:
            if not progress.has("finished"):
                solver = result.solver
                progress.emit("finished", outcome=solver.outcome, cost_ore=solver.objective_value_ore,
                              bound_ore=solver.best_objective_bound_ore, cancelled=bool(cancelled))
        except Exception:
            LOG.warning("the finished event could not be built", exc_info=True)
    return result


def resources_event(progress: ProgressSink | None, budget: Any) -> None:
    """Report the resolved compute budget: the most simultaneous day checks it allows and the workers each then gets."""
    if progress is None:
        return
    try:
        threads = budget.threads
        if not budget.parallel_day_checks:
            parallel = 1
        elif budget.workers_per_check > 0:
            parallel = min(threads, max(1, threads // budget.workers_per_check))
        else:
            parallel = threads
        emit(progress, "resources", threads=threads, memory_mb=budget.memory_mb, parallel_checks=parallel,
                      workers_per_check=max(1, threads // parallel))
    except Exception:
        LOG.warning("the resources event could not be built", exc_info=True)


def read_events(path: Path) -> list[dict[str, Any]]:
    """The events of a saved log. A line that is not complete JSON (a log cut off mid-write) is skipped."""
    events: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("seq"), int):
            events.append(event)
    return events
