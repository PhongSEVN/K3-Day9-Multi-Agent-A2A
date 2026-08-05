"""Verifier Agent: final deterministic QA gate before a case is written out.

Checks schema conformance, entity/evidence count limits, and that every
evidence ID can actually be resolved against the CSV data (catching the
false-positive evidence case the README calls out explicitly). Raises on
failure instead of silently writing a bad file.
"""
from __future__ import annotations

import json
import re

from pydantic import ValidationError

from ..data_store import DataStore
from ..logger import log_event
from ..schema import CaseOutput
from .base_agent import BaseAgent

_ORDER_RE = re.compile(r"^order:(?P<order_id>[^:]+)$")
_ITEM_RE = re.compile(r"^item:(?P<order_id>[^:]+):(?P<item_id>\d+)$")
_PAYMENT_RE = re.compile(r"^payment:(?P<order_id>[^:]+):(?P<seq>\d+)$")
_SELLER_RE = re.compile(r"^seller:(?P<seller_id>[^:]+)$")
_POLICY_RE = re.compile(r"^policy:(?P<code>[A-Z_]+)$")


class VerifierAgent(BaseAgent):
    name = "verifier_agent"
    system_prompt = (
        "You are the Verifier Agent performing final QA in an e-commerce "
        "dispute pipeline. You are given the assembled case output and a "
        "list of any structural issues already found deterministically. "
        "State PASS in one short sentence if the issue list is empty, or "
        "summarize the issues in one sentence otherwise. You cannot change "
        "any value in the case output."
    )

    def _evidence_issue(self, evidence_id: str, order_id: str, store: DataStore) -> str | None:
        if m := _ORDER_RE.match(evidence_id):
            if store.get_order(m.group("order_id")) is None:
                return f"order not found: {evidence_id}"
            return None
        if m := _ITEM_RE.match(evidence_id):
            if not store.item_exists(m.group("order_id"), int(m.group("item_id"))):
                return f"item not found: {evidence_id}"
            return None
        if m := _PAYMENT_RE.match(evidence_id):
            if not store.payment_exists(m.group("order_id"), int(m.group("seq"))):
                return f"payment not found: {evidence_id}"
            return None
        if m := _SELLER_RE.match(evidence_id):
            if not store.seller_exists(m.group("seller_id")):
                return f"seller not found: {evidence_id}"
            return None
        if _POLICY_RE.match(evidence_id):
            return None
        return f"malformed evidence id: {evidence_id}"

    def run(self, case_id: str, payload: dict, store: DataStore, order_id: str) -> dict:
        issues: list[str] = []

        try:
            CaseOutput.model_validate(payload)
        except ValidationError as exc:
            issues.append(f"schema validation failed: {exc}")

        for evidence_id in payload.get("evidence_ids", []):
            issue = self._evidence_issue(evidence_id, order_id, store)
            if issue:
                issues.append(issue)

        log_event(case_id, self.name, "verification", issues=issues)
        self.narrate(case_id, json.dumps({"issues": issues}, ensure_ascii=False))

        if issues:
            raise ValueError(f"{case_id} failed verification: {issues}")
        return payload
