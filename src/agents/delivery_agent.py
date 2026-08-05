"""Delivery Agent (owner: Vu Huy Hoang).

Compares actual delivery timing against the customer's estimated date,
and reuses Order & Seller Agent's per-seller handoff violations to
attribute a late delivery to the seller or to the logistics provider
(README.md section 4).
"""

import pandas as pd

from .. import llm_client, trace_logger

SYSTEM_PROMPT = (
    "You are the Delivery agent in an e-commerce dispute pipeline. You are "
    "given delivery timestamps and a seller-violation flag already computed "
    "from the source database. Rate how clearly these facts support the "
    "late-delivery classification. Do not invent any date not present in "
    "the facts."
)


def analyze(case_id: str, order_id: str, order: dict, seller_violations: list) -> dict:
    delivered_customer = pd.to_datetime(order.get("order_delivered_customer_date"), errors="coerce")
    estimated = pd.to_datetime(order.get("order_estimated_delivery_date"), errors="coerce")

    late_delivery = bool(
        pd.notna(delivered_customer) and pd.notna(estimated) and delivered_customer > estimated
    )

    late_cause_candidate = None
    if late_delivery:
        late_cause_candidate = "late_delivery_seller" if seller_violations else "late_delivery_logistics"

    result = {
        "late_delivery": late_delivery,
        "late_cause_candidate": late_cause_candidate,
        "delivered_customer_date": order.get("order_delivered_customer_date"),
        "estimated_delivery_date": order.get("order_estimated_delivery_date"),
    }

    trace_logger.log_event(
        case_id, "delivery_agent", "compare_timing",
        detail={
            "order_id": order_id,
            "late_delivery": late_delivery,
            "late_cause_candidate": late_cause_candidate,
            "seller_violations": seller_violations,
        },
    )

    llm_result = llm_client.call_llm_finding(
        "delivery_agent",
        SYSTEM_PROMPT,
        {
            "late_delivery": late_delivery,
            "late_cause_candidate": late_cause_candidate,
            "seller_violation_count": len(seller_violations),
        },
    )
    trace_logger.log_event(
        case_id, "delivery_agent", "llm_finding",
        detail=llm_result, latency_ms=llm_result.get("latency_ms"),
    )
    result["llm_finding"] = llm_result

    return result
