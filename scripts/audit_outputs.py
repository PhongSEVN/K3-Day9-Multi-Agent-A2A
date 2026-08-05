"""Independent audit of output/EC_XXX.json against the raw Olist CSVs.

Deliberately does NOT import src/policy_rules.py or src/agents/* — it
re-derives the expected decision straight from pandas so a bug shared by
the pipeline's own rule engine can't hide from this check. Run after
run_pipeline.py to sanity-check the 50 outputs before zipping.

Usage:
    python scripts/audit_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
TOLERANCE = 0.10

ROOT_CAUSE = {
    "canceled_order_paid": "ORDER_CANCELED_AFTER_PAYMENT",
    "unavailable_order_paid": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "late_delivery_seller": "SELLER_HANDOFF_AFTER_LIMIT",
    "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "valid_split_payment": "MULTIPLE_PAYMENTS_RECONCILED",
    "unsupported_late_claim": "DELIVERY_WITHIN_ESTIMATE",
}
ACTION = {
    "canceled_order_paid": "issue_full_refund",
    "unavailable_order_paid": "issue_full_refund",
    "late_delivery_seller": "refund_freight",
    "late_delivery_logistics": "refund_freight",
    "valid_split_payment": "explain_valid_split_payment",
    "unsupported_late_claim": "reject_late_refund",
}


def load_data():
    orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv", dtype=str)
    items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv", dtype=str)
    payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv", dtype=str)

    for col in [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    items["price"] = pd.to_numeric(items["price"], errors="coerce")
    items["freight_value"] = pd.to_numeric(items["freight_value"], errors="coerce")
    items["shipping_limit_date"] = pd.to_datetime(items["shipping_limit_date"], errors="coerce")
    payments["payment_value"] = pd.to_numeric(payments["payment_value"], errors="coerce")

    return orders, items, payments


def expected_decision(order_id: str, orders, items, payments):
    order_rows = orders[orders["order_id"] == order_id]
    if order_rows.empty:
        return None  # order not found — can't independently verify
    order = order_rows.iloc[0]

    order_items = items[items["order_id"] == order_id]
    order_payments = payments[payments["order_id"] == order_id]

    item_total = round(float(order_items["price"].sum()), 2)
    freight_total = round(float(order_items["freight_value"].sum()), 2)
    payment_total = round(float(order_payments["payment_value"].sum()), 2)

    status = order["order_status"]
    estimated = order["order_estimated_delivery_date"]
    delivered_customer = order["order_delivered_customer_date"]
    carrier_date = order["order_delivered_carrier_date"]

    if status == "canceled" and payment_total > 0:
        return "canceled_order_paid", [], round(payment_total, 2)
    if status == "unavailable" and payment_total > 0:
        return "unavailable_order_paid", [], round(payment_total, 2)

    if pd.notna(delivered_customer) and pd.notna(estimated):
        late = delivered_customer > estimated
    else:
        late = None

    if late is True:
        late_sellers = []
        for seller_id, grp in order_items.groupby("seller_id"):
            if pd.notna(carrier_date) and (
                (grp["shipping_limit_date"] < carrier_date).any()
            ):
                late_sellers.append(seller_id)
        if late_sellers:
            return "late_delivery_seller", sorted(late_sellers), round(freight_total, 2)
        return "late_delivery_logistics", [], round(freight_total, 2)

    reconciled = abs(payment_total - (item_total + freight_total)) <= TOLERANCE
    if len(order_payments) >= 2 and reconciled:
        return "valid_split_payment", [], 0.0
    if late is False and reconciled:
        return "unsupported_late_claim", [], 0.0

    return "UNMATCHED", [], None


def audit() -> int:
    orders, items, payments = load_data()
    input_files = sorted(INPUT_DIR.glob("EC_*.json"))

    total = 0
    passed = 0
    problems: list[str] = []

    for path in input_files:
        case = json.loads(path.read_text(encoding="utf-8"))
        case_id = case["case_id"]
        order_id = case["customer_request"]["claimed_order_id"]

        out_path = OUTPUT_DIR / path.name
        if not out_path.exists():
            problems.append(f"{case_id}: missing output file")
            continue
        output = json.loads(out_path.read_text(encoding="utf-8"))
        total += 1

        expected = expected_decision(order_id, orders, items, payments)
        if expected is None:
            problems.append(f"{case_id}: claimed_order_id {order_id} not found in orders.csv")
            continue

        exp_issue, exp_late_sellers, exp_refund = expected
        actual_issue = output["assessment"]["primary_issue"]
        actual_refund = output["financial_resolution"]["recommended_refund_brl"]
        actual_root_cause = output["root_cause_analysis"]["ranked_causes"][0]["cause_code"] if output["root_cause_analysis"]["ranked_causes"] else None
        actual_action = output["resolution_actions"][0] if output["resolution_actions"] else None
        actual_sellers = sorted(
            p["party_id"] for p in output["root_cause_analysis"]["responsible_parties"] if p["party_type"] == "seller"
        )

        case_ok = True
        if exp_issue == "UNMATCHED":
            problems.append(f"{case_id}: no rule matched independently (data ambiguous) — manual review needed")
            case_ok = False
        else:
            if actual_issue != exp_issue:
                problems.append(f"{case_id}: primary_issue mismatch — output={actual_issue} expected={exp_issue}")
                case_ok = False
            if actual_root_cause != ROOT_CAUSE.get(exp_issue):
                problems.append(f"{case_id}: root_cause mismatch — output={actual_root_cause} expected={ROOT_CAUSE.get(exp_issue)}")
                case_ok = False
            if actual_action != ACTION.get(exp_issue):
                problems.append(f"{case_id}: action mismatch — output={actual_action} expected={ACTION.get(exp_issue)}")
                case_ok = False
            if exp_refund is not None and abs(actual_refund - exp_refund) > 0.01:
                problems.append(f"{case_id}: refund mismatch — output={actual_refund} expected={exp_refund}")
                case_ok = False
            if exp_issue == "late_delivery_seller" and actual_sellers != exp_late_sellers:
                problems.append(f"{case_id}: late sellers mismatch — output={actual_sellers} expected={exp_late_sellers}")
                case_ok = False

        # Independent financial recompute, always checked regardless of rule match.
        order_items = items[items["order_id"] == order_id]
        order_payments = payments[payments["order_id"] == order_id]
        exp_item_total = round(float(order_items["price"].sum()), 2)
        exp_freight_total = round(float(order_items["freight_value"].sum()), 2)
        exp_payment_total = round(float(order_payments["payment_value"].sum()), 2)
        fin = output["financial_resolution"]
        if abs(fin["item_total_brl"] - exp_item_total) > 0.01:
            problems.append(f"{case_id}: item_total_brl mismatch — output={fin['item_total_brl']} expected={exp_item_total}")
            case_ok = False
        if abs(fin["freight_total_brl"] - exp_freight_total) > 0.01:
            problems.append(f"{case_id}: freight_total_brl mismatch — output={fin['freight_total_brl']} expected={exp_freight_total}")
            case_ok = False
        if abs(fin["payment_total_brl"] - exp_payment_total) > 0.01:
            problems.append(f"{case_id}: payment_total_brl mismatch — output={fin['payment_total_brl']} expected={exp_payment_total}")
            case_ok = False

        if case_ok:
            passed += 1

    print(f"Audited {total} cases against raw CSV data.")
    print(f"Fully matched independent recompute: {passed}/{total}")
    if problems:
        print(f"\n{len(problems)} issue(s) found:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("No discrepancies found.")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(audit())
