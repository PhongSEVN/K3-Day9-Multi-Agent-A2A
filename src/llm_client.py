"""Thin wrapper around the OpenAI SDK shared by every agent.

Model name is declared here in source (per README.md section 9 note 4),
never in .env — .env only holds the secret key. Every agent call goes
through call_llm_finding() so trace_logger can record latency/errors
uniformly.
"""

import json
import os
import threading
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Declared explicitly in code and mirrored in metadata.json.
MODEL_NAME = "gpt-4o-mini"

_client = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        # run_pipeline.py calls this from a thread pool; guard the
        # lazy-init so concurrent first calls don't race to construct it.
        with _client_lock:
            if _client is None:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY not set in .env")
                _client = OpenAI(api_key=api_key)
    return _client


def call_llm_finding(agent_name: str, system_prompt: str, facts: dict) -> dict:
    """Asks the model to rate confidence/rationale over facts already
    computed deterministically. The model must not invent facts or
    change any id/amount — it only reports how well the facts support
    the deterministic conclusion.

    Returns a dict with keys: confidence (float 0..1), rationale (str),
    latency_ms (float), error (str or None).
    """
    started = time.time()
    user_content = (
        "Facts (already verified against the source data, do not invent anything new):\n"
        + json.dumps(facts, ensure_ascii=False, default=str)
        + "\n\nRespond with a JSON object: "
        '{"confidence": <0..1 float>, "rationale": "<one short sentence>"}'
    )
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        confidence = float(parsed.get("confidence", 0.7))
        confidence = max(0.0, min(1.0, confidence))
        rationale = str(parsed.get("rationale", ""))[:400]
        return {
            "agent": agent_name,
            "confidence": confidence,
            "rationale": rationale,
            "latency_ms": round((time.time() - started) * 1000, 1),
            "error": None,
        }
    except Exception as exc:  # network/rate-limit/parse errors must not stop the pipeline
        return {
            "agent": agent_name,
            "confidence": 0.7,
            "rationale": "LLM call failed, deterministic rule result used as-is.",
            "latency_ms": round((time.time() - started) * 1000, 1),
            "error": str(exc),
        }
