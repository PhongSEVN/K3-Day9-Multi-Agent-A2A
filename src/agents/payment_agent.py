"""Payment Agent (owner: Nguyen Thanh Phuc).

Reconciles order_payments against item price + freight for the order.
Olist has no refund ledger, so "reconciled" simply means the totals
match within the 0.10 BRL tolerance from README.md section 4.
"""

from .. import data_loader, llm_client, trace_logger

SYSTEM_PROMPT = (
    "You are the Payment agent in an e-commerce dispute pipeline. You are "
    "given payment and item totals already computed from the source "
    "database. Rate how clearly these totals support (or contradict) a "
    "clean reconciliation. Do not invent any amount not present in the "
    "facts."
)

RECONCILE_TOLERANCE_BRL = 0.10


def analyze(case_id: str, order_id: str, items: list) -> dict:
    payments = data_loader.get_payments(order_id)

    item_total = round(sum(item["price"] for item in items), 2)
    freight_total = round(sum(item["freight_value"] for item in items), 2)
    payment_total = round(sum(p["payment_value"] for p in payments), 2)

    expected_total = round(item_total + freight_total, 2)
    reconciled = abs(payment_total - expected_total) <= RECONCILE_TOLERANCE_BRL

    result = {
        "payments": payments,
        "item_total_brl": item_total,
        "freight_total_brl": freight_total,
        "payment_total_brl": payment_total,
        "reconciled": reconciled,
    }

    trace_logger.log_event(
        case_id, "payment_agent", "reconcile",
        detail={
            "order_id": order_id,
            "payment_count": len(payments),
            "item_total_brl": item_total,
            "freight_total_brl": freight_total,
            "payment_total_brl": payment_total,
            "reconciled": reconciled,
        },
    )

    llm_result = llm_client.call_llm_finding(
        "payment_agent",
        SYSTEM_PROMPT,
        {
            "payment_count": len(payments),
            "item_total_brl": item_total,
            "freight_total_brl": freight_total,
            "payment_total_brl": payment_total,
            "reconciled": reconciled,
        },
    )
    trace_logger.log_event(
        case_id, "payment_agent", "llm_finding",
        detail=llm_result, latency_ms=llm_result.get("latency_ms"),
    )
    result["llm_finding"] = llm_result

    return result
