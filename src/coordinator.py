"""Coordinator Agent: orchestrates the per-case pipeline and A2A handoffs."""
from __future__ import annotations

from .agents.delivery_agent import DeliveryAgent
from .agents.order_seller_agent import OrderSellerAgent
from .agents.payment_agent import PaymentAgent
from .agents.policy_agent import PolicyAgent
from .agents.verifier_agent import VerifierAgent
from .data_store import DataStore
from .logger import log_event
from .output_builder import build_output


class Coordinator:
    name = "coordinator"

    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.order_seller_agent = OrderSellerAgent()
        self.delivery_agent = DeliveryAgent()
        self.payment_agent = PaymentAgent()
        self.policy_agent = PolicyAgent()
        self.verifier_agent = VerifierAgent()

    def process_case(self, case: dict) -> dict:
        case_id = case["case_id"]
        order_id = case["customer_request"]["claimed_order_id"]

        log_event(case_id, self.name, "case_received", claimed_order_id=order_id)

        order_facts = self.order_seller_agent.run(case_id, self.store, order_id)
        delivery_facts = self.delivery_agent.run(case_id, self.store, order_id)
        payment_facts = self.payment_agent.run(
            case_id, self.store, order_id, order_facts.item_total, order_facts.freight_total
        )

        decision = self.policy_agent.run(case_id, order_facts, delivery_facts, payment_facts)

        payload = build_output(case_id, order_id, order_facts, payment_facts, decision)
        payload = self.verifier_agent.run(case_id, payload, self.store, order_id)

        log_event(
            case_id,
            self.name,
            "case_completed",
            primary_issue=decision.primary_issue,
            case_status=decision.case_status,
        )
        return payload
