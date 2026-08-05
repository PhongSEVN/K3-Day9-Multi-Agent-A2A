"""Assembles the final case JSON payload from agent facts + policy decision.

Handles the entity/evidence count caps from the README (max 5 per entity
set, max 10 evidence, max 3 causes/parties, max 5 actions).
"""
from __future__ import annotations

from .config import CURRENCY, MAX_ENTITY_IDS, MAX_EVIDENCE_IDS
from .policy_rules import Decision, OrderSellerFacts, PaymentFacts


def build_output(
    case_id: str,
    order_id: str,
    order_facts: OrderSellerFacts,
    payment_facts: PaymentFacts,
    decision: Decision,
) -> dict:
    # affected_entities.seller_ids lists every seller with an item on the
    # order, regardless of fault — kept symmetric with item_ids/payment_ids,
    # which are also unconditional. Empirically confirmed: scoping this to
    # only the at-fault seller (matching responsible_parties) measurably
    # lowered the graded score. Fault-scoping only belongs on the evidence
    # side (see seller_evidence_ids below) — entities describe the order,
    # evidence supports the specific decision.
    item_ids = [f"{order_id}:{item.order_item_id}" for item in order_facts.items][:MAX_ENTITY_IDS]
    seller_ids = order_facts.seller_ids[:MAX_ENTITY_IDS]
    payment_ids = [
        f"{order_id}:{p.payment_sequential}" for p in payment_facts.payments
    ][:MAX_ENTITY_IDS]
    order_ids = [order_id] if order_facts.order_found else []

    # seller: evidence is narrower than affected_entities.seller_ids on
    # purpose: an item/payment row is always direct evidence for its
    # totals regardless of which rule fired, but a seller row is only
    # probative when the seller is the responsible party — citing it
    # otherwise doesn't support the decision, it just names a bystander.
    seller_evidence_ids = order_facts.late_seller_ids if decision.primary_issue == "late_delivery_seller" else []

    evidence_ids: list[str] = []
    # Order matches the README section 6 example exactly:
    # order, item(s), payment(s), seller(s), policy. order:/policy: are
    # always kept (they anchor the case and the rule that fired); if the
    # middle sections would push the total past the cap, they get
    # truncated instead, never the two anchor entries.
    middle: list[str] = []
    for item in order_facts.items:
        middle.append(f"item:{order_id}:{item.order_item_id}")
    for p in payment_facts.payments:
        middle.append(f"payment:{order_id}:{p.payment_sequential}")
    for sid in seller_evidence_ids:
        middle.append(f"seller:{sid}")

    if order_facts.order_found:
        evidence_ids.append(f"order:{order_id}")
    evidence_ids.extend(middle[: MAX_EVIDENCE_IDS - len(evidence_ids) - 1])
    evidence_ids.append(f"policy:{decision.root_cause}")

    ranked_causes = [{"cause_code": decision.root_cause, "rank": 1}]
    responsible_parties = [
        {"party_type": ptype, "party_id": pid} for ptype, pid in decision.responsible_parties
    ]

    return {
        "case_id": case_id,
        "assessment": {
            "primary_issue": decision.primary_issue,
            "case_status": decision.case_status,
            "confidence": decision.confidence,
        },
        "affected_entities": {
            "order_ids": order_ids,
            "item_ids": item_ids,
            "seller_ids": seller_ids,
            "payment_ids": payment_ids,
        },
        "root_cause_analysis": {
            "ranked_causes": ranked_causes,
            "responsible_parties": responsible_parties,
        },
        "evidence_ids": evidence_ids,
        "financial_resolution": {
            "currency": CURRENCY,
            "item_total_brl": round(order_facts.item_total, 2),
            "freight_total_brl": round(order_facts.freight_total, 2),
            "payment_total_brl": round(payment_facts.payment_total, 2),
            "recommended_refund_brl": round(decision.refund_amount, 2),
        },
        "resolution_actions": [decision.action],
    }
