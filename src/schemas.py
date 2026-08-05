"""Output schema helpers and limits (README.md section 6).

Verifier Agent is the single place that enforces these limits; other
agents just hand off structured Python dicts.
"""

from . import data_loader

MAX_ENTITY_IDS = 5
MAX_EVIDENCE_IDS = 10
MAX_ROOT_CAUSES = 3
MAX_RESPONSIBLE_PARTIES = 3
MAX_ACTIONS = 5

VALID_PRIMARY_ISSUES = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
}

VALID_ROOT_CAUSE_CODES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}


def evidence_order(order_id: str) -> str:
    return f"order:{order_id}"


def evidence_item(order_id: str, order_item_id) -> str:
    return f"item:{order_id}:{order_item_id}"


def evidence_payment(order_id: str, payment_sequential) -> str:
    return f"payment:{order_id}:{payment_sequential}"


def evidence_seller(seller_id: str) -> str:
    return f"seller:{seller_id}"


def evidence_policy(root_cause_code: str) -> str:
    return f"policy:{root_cause_code}"


def evidence_id_is_grounded(evidence_id: str, order_id: str) -> bool:
    """True only if the evidence id is well-formed AND resolves to a
    real row in the loaded CSVs (README.md section 5)."""
    parts = evidence_id.split(":")
    if len(parts) < 2:
        return False
    kind = parts[0]

    if kind == "order":
        return len(parts) == 2 and parts[1] == order_id and data_loader.order_exists(order_id)
    if kind == "item":
        if len(parts) != 3 or parts[1] != order_id:
            return False
        try:
            item_id = int(parts[2])
        except ValueError:
            return False
        return data_loader.item_exists(order_id, item_id)
    if kind == "payment":
        if len(parts) != 3 or parts[1] != order_id:
            return False
        try:
            seq = int(parts[2])
        except ValueError:
            return False
        return data_loader.payment_exists(order_id, seq)
    if kind == "seller":
        return len(parts) == 2 and data_loader.seller_exists(parts[1])
    if kind == "policy":
        return len(parts) == 2 and parts[1] in VALID_ROOT_CAUSE_CODES
    return False


def build_output_skeleton(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "assessment": {
            "primary_issue": None,
            "case_status": None,
            "confidence": 0.0,
        },
        "affected_entities": {
            "order_ids": [],
            "item_ids": [],
            "seller_ids": [],
            "payment_ids": [],
        },
        "root_cause_analysis": {
            "ranked_causes": [],
            "responsible_parties": [],
        },
        "evidence_ids": [],
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": 0.0,
            "freight_total_brl": 0.0,
            "payment_total_brl": 0.0,
            "recommended_refund_brl": 0.0,
        },
        "resolution_actions": [],
    }
