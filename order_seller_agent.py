"""Order and seller specialist for the dispute-resolution pipeline."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from model_config import MODEL_NAME, MODEL_PARAMETER_SIZE


@dataclass(frozen=True)
class OrderSellerHandoff:
    case_id: str
    order_id: str
    order_status: str
    item_ids: list[str]
    seller_ids: list[str]
    item_total_brl: float
    freight_total_brl: float
    order_evidence_id: str
    item_evidence_ids: list[str]
    seller_evidence_ids: list[str]


class OrderSellerAgent:
    """Resolve order state, item ownership and order-side financial totals."""

    def __init__(self, data_dir: Path | str = "data") -> None:
        data_dir = Path(data_dir)
        with (data_dir / "olist_orders_dataset.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            self.orders = {row["order_id"]: row for row in csv.DictReader(stream)}

        self.items: dict[str, list[dict[str, str]]] = {}
        with (data_dir / "olist_order_items_dataset.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            for row in csv.DictReader(stream):
                self.items.setdefault(row["order_id"], []).append(row)

    def investigate(self, case_id: str, order_id: str) -> OrderSellerHandoff:
        if order_id not in self.orders:
            raise ValueError(f"Unknown order_id: {order_id}")
        items = sorted(
            self.items.get(order_id, []), key=lambda row: int(row["order_item_id"])
        )
        item_ids = [f'{order_id}:{row["order_item_id"]}' for row in items]
        seller_ids = list(dict.fromkeys(row["seller_id"] for row in items))
        return OrderSellerHandoff(
            case_id=case_id,
            order_id=order_id,
            order_status=self.orders[order_id]["order_status"],
            item_ids=item_ids[:5],
            seller_ids=seller_ids[:5],
            item_total_brl=round(sum((float(row["price"]) for row in items), 0.0), 2),
            freight_total_brl=round(
                sum((float(row["freight_value"]) for row in items), 0.0), 2
            ),
            order_evidence_id=f"order:{order_id}",
            item_evidence_ids=[f"item:{item_id}" for item_id in item_ids[:5]],
            seller_evidence_ids=[f"seller:{seller_id}" for seller_id in seller_ids[:5]],
        )
