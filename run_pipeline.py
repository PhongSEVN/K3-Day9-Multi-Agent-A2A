"""Entry point: run the full multi-agent pipeline over input/EC_*.json.

Usage:
    python run_pipeline.py
"""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone

import openai
import pandas
import pydantic

from src.config import (
    INPUT_DIR,
    METADATA_PATH,
    OPENAI_MODEL,
    OPENAI_MODEL_PARAM_NOTE,
    OUTPUT_DIR,
    POLICY_VERSION,
)
from src.coordinator import Coordinator
from src.data_store import DataStore
from src.logger import log_event, reset_trace


def write_metadata(*, total_cases: int, succeeded: int, failed: int, started_at: str, finished_at: str) -> None:
    metadata = {
        "run": {
            "started_at": started_at,
            "finished_at": finished_at,
            "total_cases": total_cases,
            "succeeded": succeeded,
            "failed": failed,
        },
        "policy_version": POLICY_VERSION,
        "model": {
            "name": OPENAI_MODEL,
            "provider": "OpenAI",
            "parameter_size": OPENAI_MODEL_PARAM_NOTE,
            "role": "reasoning/handoff narration only; all decision fields are computed by the deterministic rule engine (src/policy_rules.py)",
        },
        "agents": [
            "coordinator",
            "order_seller_agent",
            "delivery_agent",
            "payment_agent",
            "policy_agent",
            "verifier_agent",
        ],
        "framework": "custom Python multi-agent pipeline (no third-party agent framework); openai SDK for LLM calls, pandas for data access, pydantic for schema validation",
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "openai_sdk": openai.__version__,
            "pandas": pandas.__version__,
            "pydantic": pydantic.__version__,
        },
    }
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    started_at = datetime.now(timezone.utc).isoformat()
    reset_trace()

    store = DataStore()
    coordinator = Coordinator(store)

    input_files = sorted(INPUT_DIR.glob("EC_*.json"))
    if not input_files:
        print(f"No input files found in {INPUT_DIR}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    succeeded = 0
    failures: list[dict] = []

    for path in input_files:
        case = json.loads(path.read_text(encoding="utf-8"))
        case_id = case.get("case_id", path.stem)
        try:
            output = coordinator.process_case(case)
        except Exception as exc:  # noqa: BLE001 - one bad case must not abort the run
            failures.append({"case_id": case_id, "error": str(exc)})
            log_event(case_id, "coordinator", "case_failed", error=str(exc))
            print(f"[FAIL] {case_id}: {exc}")
            continue

        out_path = OUTPUT_DIR / path.name
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        succeeded += 1
        print(f"[OK]   {case_id} -> {output['assessment']['primary_issue']}")

    finished_at = datetime.now(timezone.utc).isoformat()
    write_metadata(
        total_cases=len(input_files),
        succeeded=succeeded,
        failed=len(failures),
        started_at=started_at,
        finished_at=finished_at,
    )

    print(f"\nProcessed {succeeded}/{len(input_files)} cases.")
    if failures:
        print(f"{len(failures)} case(s) failed:")
        for f in failures:
            print(f"  {f['case_id']}: {f['error']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
