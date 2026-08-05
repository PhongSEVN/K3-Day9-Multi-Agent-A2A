"""Shared base class for every domain agent.

Each concrete agent owns one data domain, computes facts deterministically
via DataStore (a "tool call", logged as event=tool_result), then asks the
LLM for a short handoff/rationale note scoped to only its own facts
(logged as event=llm_note). The LLM never sees the full case end-to-end
and never authors a decision field directly — this is what keeps the
pipeline genuinely multi-agent instead of one prompt doing everything.
"""
from __future__ import annotations

from ..config import OPENAI_MODEL
from ..llm_client import LLMUnavailableError, call_agent_llm
from ..logger import log_event


class BaseAgent:
    name: str = "base_agent"
    system_prompt: str = "You are a helpful assistant."

    def narrate(self, case_id: str, user_prompt: str, *, max_tokens: int = 220) -> str:
        try:
            text = call_agent_llm(self.system_prompt, user_prompt, max_tokens=max_tokens)
        except LLMUnavailableError as exc:
            text = f"[llm_unavailable] {exc}"
        except Exception as exc:  # network/timeout/rate-limit — never fail the case for this
            text = f"[llm_error] {exc}"
        log_event(
            case_id,
            self.name,
            "llm_note",
            model=OPENAI_MODEL,
            prompt=user_prompt,
            response=text,
        )
        return text
