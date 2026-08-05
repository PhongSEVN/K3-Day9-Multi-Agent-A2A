"""Delivery-domain agent for the Olist dispute-resolution pipeline.

The classification is intentionally deterministic because all relevant facts are
available in the CSV files.  MODEL_NAME documents the <=10B model assigned to
this custom agent when a coordinator/provider adds natural-language reasoning.
Secrets are never accepted by this module and belong in an uncommitted .env.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MODEL_PARAMETER_SIZE = "7B"
AGENT_NAME = "delivery_agent"


def _timestamp(value: str) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


@dataclass(frozen=True)
class DeliveryHandoff:
    case_id: str
    order_id: str
    delivery_status: str
    delivered_late: Optional[bool]
    carrier_handoff_after_limit: Optional[bool]
    violating_item_ids: list[str]
    violating_seller_ids: list[str]
    suggested_cause_code: Optional[str]
    order_evidence_id: str
    item_evidence_ids: list[str]
    facts: dict[str, Optional[str]]


class DeliveryAgent:
    """Read-only specialist for delivery dates and carrier handoff deadlines."""

    def __init__(self, data_dir: Path | str = "data") -> None:
        data_dir = Path(data_dir)
        self.orders: dict[str, dict[str, str]] = {}
        self.items: dict[str, list[dict[str, str]]] = {}

        with (data_dir / "olist_orders_dataset.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            self.orders = {row["order_id"]: row for row in csv.DictReader(stream)}

        with (data_dir / "olist_order_items_dataset.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            for row in csv.DictReader(stream):
                self.items.setdefault(row["order_id"], []).append(row)

    def investigate(self, case_id: str, order_id: str) -> DeliveryHandoff:
        if order_id not in self.orders:
            raise ValueError(f"Unknown order_id: {order_id}")

        order = self.orders[order_id]
        delivered = _timestamp(order["order_delivered_customer_date"])
        estimate = _timestamp(order["order_estimated_delivery_date"])
        carrier = _timestamp(order["order_delivered_carrier_date"])

        delivered_late = (
            delivered > estimate if delivered is not None and estimate is not None else None
        )
        violations: list[dict[str, str]] = []
        if carrier is not None:
            for item in self.items.get(order_id, []):
                limit = _timestamp(item["shipping_limit_date"])
                if limit is not None and carrier > limit:
                    violations.append(item)

        if delivered_late is True and violations:
            status = "late_seller_handoff"
            cause = "SELLER_HANDOFF_AFTER_LIMIT"
        elif delivered_late is True:
            status = "late_logistics"
            cause = "CARRIER_DELIVERED_AFTER_ESTIMATE"
        elif delivered_late is False:
            status = "within_estimate"
            cause = "DELIVERY_WITHIN_ESTIMATE"
        else:
            status = "not_delivered_or_dates_missing"
            cause = None

        violating_item_ids = [
            f'{order_id}:{item["order_item_id"]}' for item in violations
        ]
        violating_seller_ids = list(dict.fromkeys(item["seller_id"] for item in violations))
        handoff_after_limit = bool(violations) if carrier is not None else None

        return DeliveryHandoff(
            case_id=case_id,
            order_id=order_id,
            delivery_status=status,
            delivered_late=delivered_late,
            carrier_handoff_after_limit=handoff_after_limit,
            violating_item_ids=violating_item_ids[:5],
            violating_seller_ids=violating_seller_ids[:5],
            suggested_cause_code=cause,
            order_evidence_id=f"order:{order_id}",
            item_evidence_ids=[f"item:{item_id}" for item_id in violating_item_ids[:5]],
            facts={
                "order_delivered_carrier_date": order["order_delivered_carrier_date"] or None,
                "order_delivered_customer_date": order["order_delivered_customer_date"] or None,
                "order_estimated_delivery_date": order["order_estimated_delivery_date"] or None,
            },
        )


def _write_trace(path: Path, result: DeliveryHandoff) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "agent": AGENT_NAME,
        "event": "delivery_investigation_completed",
        "case_id": result.case_id,
        "order_id": result.order_id,
        "handoff": asdict(result),
    }
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Delivery Agent for Olist cases")
    parser.add_argument("--input-dir", default="input")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--trace", default="logging/trace.jsonl")
    parser.add_argument("--reset-trace", action="store_true")
    args = parser.parse_args()

    trace_path = Path(args.trace)
    if args.reset_trace:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text("", encoding="utf-8")

    agent = DeliveryAgent(args.data_dir)
    count = 0
    for case_path in sorted(Path(args.input_dir).glob("EC_*.json")):
        case = json.loads(case_path.read_text(encoding="utf-8-sig"))
        result = agent.investigate(
            case_id=case["case_id"],
            order_id=case["customer_request"]["claimed_order_id"],
        )
        _write_trace(trace_path, result)
        count += 1
    print(f"Delivery Agent processed {count} cases; trace={trace_path}")


if __name__ == "__main__":
    main()

