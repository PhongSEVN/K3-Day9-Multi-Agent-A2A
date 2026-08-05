"""Append-only JSONL trace of every agent step for the current pipeline run.

README.md section 9 requires trace.jsonl to reflect only the latest run
(no cross-run append), so reset() truncates the file once at the start
of run_pipeline.py; every agent call appends one line after that.
"""

import json
import os
import threading
from datetime import datetime, timezone

_LOGGING_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logging")
_TRACE_PATH = os.path.join(_LOGGING_DIR, "trace.jsonl")
_write_lock = threading.Lock()


def reset():
    os.makedirs(_LOGGING_DIR, exist_ok=True)
    with _write_lock:
        open(_TRACE_PATH, "w", encoding="utf-8").close()


def log_event(case_id: str, agent: str, action: str, detail: dict = None, latency_ms: float = None, level: str = "info"):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "agent": agent,
        "action": action,
        "level": level,
        "latency_ms": latency_ms,
        "detail": detail or {},
    }
    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    # run_pipeline.py processes cases on a thread pool; without this lock,
    # interleaved writes from concurrent threads corrupt trace.jsonl (seen
    # in practice as JSONDecodeError on read).
    with _write_lock:
        with open(_TRACE_PATH, "a", encoding="utf-8") as f:
            f.write(line)
