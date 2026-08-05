"""Order & Seller Agent (owner: Pham Khanh Linh).

Resolves claimed_order_id against orders/order_items/sellers and flags
which seller(s), if any, handed the order to the carrier after their
own shipping_limit_date (README.md section 4 note on multi-seller
orders).
"""

import pandas as pd

from .. import data_loader, llm_client, trace_logger

SYSTEM_PROMPT = (
    "You are the Order & Seller agent in an e-commerce dispute pipeline. "
    "You are given order/item/seller facts already pulled from the source "
    "database. Rate how clearly these facts are internally consistent and "
    "complete for a downstream decision. Do not invent any id, date or "
    "amount not present in the facts."
)


def analyze(case_id: str, claimed_order_id: str) -> dict:
    order = data_loader.get_order(claimed_order_id)
    items = data_loader.get_items(claimed_order_id)

    result = {
        "order_id": claimed_order_id,
        "order_found": order is not None,
        "order": order,
        "items": items,
        "seller_ids": [],
        "seller_violations": [],
    }

    if order is None:
        trace_logger.log_event(
            case_id, "order_seller_agent", "lookup",
            detail={"claimed_order_id": claimed_order_id, "found": False},
            level="warning",
        )
        return result

    seller_ids = sorted({item["seller_id"] for item in items})
    result["seller_ids"] = seller_ids

    carrier_date = pd.to_datetime(order.get("order_delivered_carrier_date"), errors="coerce")
    violations = []
    if pd.notna(carrier_date):
        for item in items:
            limit_date = pd.to_datetime(item.get("shipping_limit_date"), errors="coerce")
            if pd.notna(limit_date) and carrier_date > limit_date:
                violations.append(item["seller_id"])
    result["seller_violations"] = sorted(set(violations))

    trace_logger.log_event(
        case_id, "order_seller_agent", "lookup",
        detail={
            "claimed_order_id": claimed_order_id,
            "order_status": order.get("order_status"),
            "item_count": len(items),
            "seller_ids": seller_ids,
            "seller_violations": result["seller_violations"],
        },
    )

    llm_result = llm_client.call_llm_finding(
        "order_seller_agent",
        SYSTEM_PROMPT,
        {
            "order_status": order.get("order_status"),
            "item_count": len(items),
            "seller_count": len(seller_ids),
            "seller_violations": result["seller_violations"],
        },
    )
    trace_logger.log_event(
        case_id, "order_seller_agent", "llm_finding",
        detail=llm_result, latency_ms=llm_result.get("latency_ms"),
    )
    result["llm_finding"] = llm_result

    return result
