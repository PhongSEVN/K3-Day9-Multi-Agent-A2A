"""Policy Agent: applies EC_POLICY_V1 to the handed-off facts."""
from __future__ import annotations

import json

from ..logger import log_event
from ..policy_rules import Decision, DeliveryFacts, OrderSellerFacts, PaymentFacts, decide
from .base_agent import BaseAgent


class PolicyAgent(BaseAgent):
    name = "policy_agent"
    system_prompt = (
        "You are the Policy Agent applying EC_POLICY_V1 in an e-commerce "
        "dispute pipeline. You are given a decision already computed "
        "deterministically by the rule engine from verified facts handed off "
        "by the Order & Seller, Delivery, and Payment agents. Write a 2-3 "
        "sentence rationale explaining why this primary_issue and "
        "responsible party follow from the facts. Do not propose a "
        "different decision — you are explaining it, not making it."
    )

    def run(
        self,
        case_id: str,
        order_facts: OrderSellerFacts,
        delivery_facts: DeliveryFacts,
        payment_facts: PaymentFacts,
    ) -> Decision:
        decision = decide(order_facts, delivery_facts, payment_facts)

        log_event(
            case_id,
            self.name,
            "decision",
            primary_issue=decision.primary_issue,
            case_status=decision.case_status,
            confidence=decision.confidence,
            root_cause=decision.root_cause,
            responsible_parties=decision.responsible_parties,
            refund_amount=decision.refund_amount,
            action=decision.action,
            fallback=decision.fallback,
        )
        self.narrate(
            case_id,
            json.dumps(
                {
                    "order_status": order_facts.order_status,
                    "late_seller_ids": order_facts.late_seller_ids,
                    "delivered_after_estimate": delivery_facts.delivered_after_estimate,
                    "payment_count": payment_facts.payment_count,
                    "decision": decision.primary_issue,
                    "responsible_parties": decision.responsible_parties,
                },
                ensure_ascii=False,
            ),
        )
        return decision
