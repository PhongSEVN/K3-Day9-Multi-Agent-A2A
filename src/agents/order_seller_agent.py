"""Order & Seller Agent: order status, items, sellers, handoff deadlines."""
from __future__ import annotations

import json

import pandas as pd

from ..data_store import DataStore
from ..logger import log_event
from ..policy_rules import ItemFact, OrderSellerFacts
from .base_agent import BaseAgent


class OrderSellerAgent(BaseAgent):
    name = "order_seller_agent"
    system_prompt = (
        "You are the Order & Seller Agent in an e-commerce dispute pipeline. "
        "You are given verified order/item/seller facts already computed from "
        "the database (not from the customer's claim). Write a 2-3 sentence "
        "handoff note for the next agent: order status, item/seller count, and "
        "whether any seller handed the order to the carrier after their own "
        "shipping_limit_date. Only use the facts given; never invent data."
    )

    def run(self, case_id: str, store: DataStore, order_id: str) -> OrderSellerFacts:
        order = store.get_order(order_id)
        if order is None:
            facts = OrderSellerFacts(order_found=False, order_status=None)
            log_event(case_id, self.name, "tool_result", order_found=False, order_id=order_id)
            self.narrate(case_id, json.dumps({"order_found": False, "order_id": order_id}))
            return facts

        items_df = store.get_items(order_id)
        carrier_date = order["order_delivered_carrier_date"]

        items: list[ItemFact] = []
        seller_ids: list[str] = []
        late_seller_ids: list[str] = []
        item_total = 0.0
        freight_total = 0.0

        for _, row in items_df.iterrows():
            price = float(row["price"]) if pd.notna(row["price"]) else 0.0
            freight = float(row["freight_value"]) if pd.notna(row["freight_value"]) else 0.0
            item_total += price
            freight_total += freight

            carrier_after_limit = bool(
                pd.notna(carrier_date)
                and pd.notna(row["shipping_limit_date"])
                and carrier_date > row["shipping_limit_date"]
            )

            item_fact = ItemFact(
                order_item_id=int(row["order_item_id"]),
                product_id=str(row["product_id"]),
                seller_id=str(row["seller_id"]),
                shipping_limit_date=row["shipping_limit_date"],
                price=round(price, 2),
                freight_value=round(freight, 2),
                carrier_after_limit=carrier_after_limit,
            )
            items.append(item_fact)

            if item_fact.seller_id not in seller_ids:
                seller_ids.append(item_fact.seller_id)
            if carrier_after_limit and item_fact.seller_id not in late_seller_ids:
                late_seller_ids.append(item_fact.seller_id)

        facts = OrderSellerFacts(
            order_found=True,
            order_status=str(order["order_status"]),
            items=items,
            seller_ids=seller_ids,
            late_seller_ids=late_seller_ids,
            item_total=round(item_total, 2),
            freight_total=round(freight_total, 2),
        )

        log_event(
            case_id,
            self.name,
            "tool_result",
            order_id=order_id,
            order_status=facts.order_status,
            item_count=len(items),
            seller_ids=seller_ids,
            late_seller_ids=late_seller_ids,
            item_total=facts.item_total,
            freight_total=facts.freight_total,
        )
        self.narrate(
            case_id,
            json.dumps(
                {
                    "order_status": facts.order_status,
                    "item_count": len(items),
                    "seller_ids": seller_ids,
                    "late_seller_ids": late_seller_ids,
                },
                ensure_ascii=False,
            ),
        )
        return facts
