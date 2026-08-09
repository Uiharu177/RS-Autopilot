"""Persistent, low-overhead diagnostics for a single trade-route run.

The recorder deliberately stores structured data next to the ordinary runtime
log.  A future investigation can therefore inspect one folder instead of
trying to correlate screenshots and a global log by hand.
"""

from __future__ import annotations

import json
import shutil
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from loguru import logger


RUNS_DIR = Path("logs") / "debug" / "runs"
_lock = threading.RLock()
_active: dict[str, Any] | None = None
_last: dict[str, Any] | None = None


def _json_default(value: Any) -> str:
    return str(value)


def _write(payload: dict[str, Any]) -> None:
    run_dir = Path(payload["directory"])
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(_serializable(payload), ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def _serializable(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip in-memory timers before writing a portable report."""
    result = dict(payload)
    result.pop("_started_perf", None)
    result.pop("_step_started_perf", None)
    return result


def _public(payload: dict[str, Any] | None, include_events: bool = True) -> dict[str, Any] | None:
    if payload is None:
        return None
    result = dict(payload)
    result["directory"] = str(Path(result["directory"]).as_posix())
    if result.get("status") == "running":
        result["duration_ms"] = round((time.perf_counter() - result["_started_perf"]) * 1000, 1)
    result.pop("_started_perf", None)
    result.pop("_step_started_perf", None)
    if not include_events:
        result.pop("events", None)
    return result


def start_trade_run(cities: list[str], planned_rounds: int) -> dict[str, Any]:
    """Start a new run and make it the active diagnostic context."""
    global _active, _last
    with _lock:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_id = f"trade-{stamp}-{time.time_ns() % 1_000_000:06d}"
        payload: dict[str, Any] = {
            "id": run_id,
            "kind": "trade",
            "status": "running",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": None,
            "duration_ms": None,
            "route": list(cities),
            "planned_rounds": int(planned_rounds),
            "current_step": "preparing",
            "current_round": None,
            "events": [],
            "failure": None,
            "snapshot": None,
            "directory": str((RUNS_DIR / run_id).resolve()),
            "_started_perf": time.perf_counter(),
            "_step_started_perf": time.perf_counter(),
        }
        _active = payload
        _last = payload
        _add_event_locked(payload, "run_started", "Run diagnostics started", {
            "route": list(cities), "planned_rounds": int(planned_rounds)
        })
        return _public(payload) or {}


def _add_event_locked(payload: dict[str, Any], event: str, message: str, details: dict[str, Any] | None = None) -> None:
    item = {
        "at": datetime.now().isoformat(timespec="milliseconds"),
        "event": event,
        "message": message,
        "details": details or {},
    }
    payload["events"].append(item)
    # A compact rolling trail is enough for diagnosis and avoids growing the
    # JSON file indefinitely during long runs.
    payload["events"][:] = payload["events"][-120:]
    _write(payload)


def record(event: str, message: str, **details: Any) -> None:
    with _lock:
        if _active is None:
            return
        _add_event_locked(_active, event, message, details)


def set_step(name: str, *, round_index: int | None = None, **details: Any) -> None:
    with _lock:
        if _active is None:
            return
        previous_step = _active.get("current_step")
        previous_started = _active.get("_step_started_perf")
        if previous_step and previous_started is not None:
            _add_event_locked(
                _active, "step_finished", previous_step,
                {"elapsed_ms": round((time.perf_counter() - previous_started) * 1000, 1)},
            )
        _active["current_step"] = name
        _active["_step_started_perf"] = time.perf_counter()
        if round_index is not None:
            _active["current_round"] = round_index
        _add_event_locked(_active, "step_started", name, details)


@contextmanager
def step(name: str, *, round_index: int | None = None, **details: Any) -> Iterator[None]:
    """Record both outcome and elapsed time for one meaningful action."""
    set_step(name, round_index=round_index, **details)
    started = time.perf_counter()
    try:
        yield
    except BaseException as exc:
        record(
            "step_failed", name,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            error=str(exc), error_type=type(exc).__name__,
        )
        raise
    else:
        record("step_finished", name, elapsed_ms=round((time.perf_counter() - started) * 1000, 1))


def finish(status: str, *, error: BaseException | None = None, capture_snapshot: bool = False) -> None:
    global _active, _last
    with _lock:
        payload = _active
        if payload is None:
            return
        payload["status"] = status
        payload["finished_at"] = datetime.now().isoformat(timespec="seconds")
        payload["duration_ms"] = round((time.perf_counter() - payload["_started_perf"]) * 1000, 1)
        payload.pop("_started_perf", None)
        step_started = payload.pop("_step_started_perf", None)
        if step_started is not None and payload.get("current_step"):
            _add_event_locked(
                payload, "step_finished", payload["current_step"],
                {"elapsed_ms": round((time.perf_counter() - step_started) * 1000, 1)},
            )
        if error is not None:
            payload["failure"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            }
        _add_event_locked(payload, "run_finished", status, {"error": str(error) if error else None})
        _last = payload
        _active = None

    # A snapshot talks to the device, so it must run outside the recorder lock.
    if capture_snapshot:
        try:
            from resonance.debug.snapshot import capture_debug_snapshot
            snapshot = capture_debug_snapshot(reason=f"diagnostic:{payload['id']}:{payload['current_step']}")
        except Exception as exc:  # Snapshot failure must never hide the original failure.
            logger.warning(f"Unable to capture failure snapshot: {exc}")
            snapshot = {"success": False, "error": str(exc)}
        with _lock:
            snapshot_dir = Path(payload["directory"]) / "failure_snapshot"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            copied_files: list[str] = []
            for key in ("screenshot", "ocr_file"):
                source_name = snapshot.get(key)
                if not source_name:
                    continue
                source = Path(source_name)
                if source.is_file():
                    target = snapshot_dir / source.name
                    shutil.copy2(source, target)
                    copied_files.append(str(target.relative_to(Path(payload["directory"])).as_posix()))
            snapshot["bundle_files"] = copied_files
            payload["snapshot"] = snapshot
            _write(payload)


def latest_run() -> dict[str, Any] | None:
    with _lock:
        return _public(_active or _last)


def export_latest_run() -> Path | None:
    """Create a portable zip containing the structured report and snapshot files."""
    with _lock:
        payload = _active or _last
        if payload is None:
            return None
        run_dir = Path(payload["directory"])
        _write(payload)
        archive_base = run_dir.parent / f"{payload['id']}-diagnostic"
        return Path(shutil.make_archive(str(archive_base), "zip", root_dir=run_dir))
