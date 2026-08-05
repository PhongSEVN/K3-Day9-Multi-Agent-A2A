"""Entrypoint: runs all input/EC_*.json cases through the agent pipeline
and writes output/EC_*.json. Run from the repo root with:

    python -m src.run_pipeline

Cases are independent of each other (each only touches its own order_id),
and each case's wall-clock time is dominated by waiting on 4 sequential
OpenAI calls (I/O-bound), so cases are fanned out across a thread pool
instead of a plain for-loop — this is what took 50 cases from ~3 minutes
down to well under a minute. trace_logger and data_loader are made
thread-safe (locks) specifically to support this; see the comments there.
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import data_loader, trace_logger
from .agents import coordinator_agent

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_INPUT_DIR = os.path.join(_ROOT, "input")
_OUTPUT_DIR = os.path.join(_ROOT, "output")
_MAX_WORKERS = 10


def _run_one(filename: str):
    in_path = os.path.join(_INPUT_DIR, filename)
    out_path = os.path.join(_OUTPUT_DIR, filename)
    with open(in_path, "r", encoding="utf-8") as f:
        case = json.load(f)

    output = coordinator_agent.process_case(case)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return output


def main():
    started = time.time()
    trace_logger.reset()
    data_loader._load()  # eager, single-threaded, before the pool starts

    input_files = sorted(f for f in os.listdir(_INPUT_DIR) if f.startswith("EC_") and f.endswith(".json"))
    if not input_files:
        print(f"No input files found in {_INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(_OUTPUT_DIR, exist_ok=True)

    ok, failed = 0, []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        future_to_filename = {pool.submit(_run_one, filename): filename for filename in input_files}
        for future in as_completed(future_to_filename):
            filename = future_to_filename[future]
            try:
                output = future.result()
            except Exception as exc:
                failed.append((filename, str(exc)))
                trace_logger.log_event(
                    filename, "run_pipeline", "case_crashed",
                    detail={"error": str(exc)}, level="error",
                )
                continue
            ok += 1
            print(f"{filename} -> {output['assessment']['primary_issue']} (confidence={output['assessment']['confidence']})")

    elapsed = round(time.time() - started, 1)
    print(f"\nDone: {ok}/{len(input_files)} cases written to {_OUTPUT_DIR} in {elapsed}s")
    if failed:
        print(f"FAILED ({len(failed)}):", file=sys.stderr)
        for filename, err in failed:
            print(f"  {filename}: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
