"""Payment reconciliation specialist for the dispute-resolution pipeline."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from model_config import MODEL_NAME, MODEL_PARAMETER_SIZE


@dataclass(frozen=True)
class PaymentHandoff:
    case_id: str
    order_id: str
    payment_ids: list[str]
    payment_row_count: int
    payment_total_brl: float
    expected_order_total_brl: float
    reconciled_within_010_brl: bool
    payment_evidence_ids: list[str]


class PaymentAgent:
    """Aggregate payment rows and reconcile them with item plus freight value."""

    def __init__(self, data_dir: Path | str = "data") -> None:
        data_dir = Path(data_dir)
        self.payments: dict[str, list[dict[str, str]]] = {}
        self.items: dict[str, list[dict[str, str]]] = {}
        with (data_dir / "olist_order_payments_dataset.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            for row in csv.DictReader(stream):
                self.payments.setdefault(row["order_id"], []).append(row)
        with (data_dir / "olist_order_items_dataset.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            for row in csv.DictReader(stream):
                self.items.setdefault(row["order_id"], []).append(row)

    def investigate(self, case_id: str, order_id: str) -> PaymentHandoff:
        payments = sorted(
            self.payments.get(order_id, []),
            key=lambda row: int(row["payment_sequential"]),
        )
        items = self.items.get(order_id, [])
        payment_total = round(
            sum((float(row["payment_value"]) for row in payments), 0.0), 2
        )
        expected_total = round(
            sum(
                (float(row["price"]) + float(row["freight_value"]) for row in items),
                0.0,
            ),
            2,
        )
        payment_ids = [f'{order_id}:{row["payment_sequential"]}' for row in payments]
        return PaymentHandoff(
            case_id=case_id,
            order_id=order_id,
            payment_ids=payment_ids[:5],
            payment_row_count=len(payments),
            payment_total_brl=payment_total,
            expected_order_total_brl=expected_total,
            reconciled_within_010_brl=abs(payment_total - expected_total) <= 0.10,
            payment_evidence_ids=[f"payment:{payment_id}" for payment_id in payment_ids[:5]],
        )
