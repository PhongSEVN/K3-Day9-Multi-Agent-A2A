"""Coordinator Agent (owner: Nguyen Van Phong).

Owns the handoff order between the domain agents (README.md section 7):
Order & Seller -> Payment -> Delivery -> Policy -> Verifier. Each step's
output dict is fed as input to the next; nothing here re-derives facts
that a specialist agent already computed.
"""

from . import delivery_agent, order_seller_agent, payment_agent, policy_agent, verifier_agent
from .. import trace_logger


def process_case(case: dict) -> dict:
    case_id = case["case_id"]
    claimed_order_id = case["customer_request"]["claimed_order_id"]

    trace_logger.log_event(case_id, "coordinator_agent", "case_start", detail={"claimed_order_id": claimed_order_id})

    order_seller = order_seller_agent.analyze(case_id, claimed_order_id)
    order = order_seller["order"] or {}

    payment = payment_agent.analyze(case_id, claimed_order_id, order_seller["items"])
    delivery = delivery_agent.analyze(case_id, claimed_order_id, order, order_seller["seller_violations"])
    policy = policy_agent.decide(case_id, claimed_order_id, order_seller, payment, delivery)
    output = verifier_agent.build(case_id, claimed_order_id, order_seller, payment, policy)

    trace_logger.log_event(case_id, "coordinator_agent", "case_end", detail={"primary_issue": output["assessment"]["primary_issue"]})

    return output
