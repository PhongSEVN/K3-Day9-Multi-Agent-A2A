"""Thin wrapper around the OpenAI Chat Completions API.

Every agent uses this only for reasoning/handoff narration (logged for A2A
traceability). No numeric or ID decision in the final output is derived
from LLM free-text output — those come from the deterministic rule engine
in policy_rules.py, so the case output is reproducible and never
hallucinated. See architecture.md for the rationale.
"""
from __future__ import annotations

from openai import OpenAI

from .config import OPENAI_API_KEY, OPENAI_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


class LLMUnavailableError(RuntimeError):
    pass


def call_agent_llm(system_prompt: str, user_prompt: str, *, max_tokens: int = 220) -> str:
    if _client is None:
        raise LLMUnavailableError("OPENAI_API_KEY not set in .env")
    response = _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    return (content or "").strip()
