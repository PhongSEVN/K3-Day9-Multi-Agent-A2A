"""Append-only JSONL trace of every agent action (A2A handoffs + LLM calls).

The lab requires the latest run's trace only (no historical append), so
`reset_trace()` truncates the file at the start of each full pipeline run.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from .config import TRACE_PATH

_lock = threading.Lock()


def reset_trace() -> None:
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACE_PATH.write_text("", encoding="utf-8")


def log_event(case_id: str, agent: str, event: str, **fields: Any) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "agent": agent,
        "event": event,
        **fields,
    }
    with _lock:
        with TRACE_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
