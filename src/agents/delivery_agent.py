"""Delivery Agent: actual delivery time vs estimated delivery deadline."""
from __future__ import annotations

import json

import pandas as pd

from ..data_store import DataStore
from ..logger import log_event
from ..policy_rules import DeliveryFacts
from .base_agent import BaseAgent


class DeliveryAgent(BaseAgent):
    name = "delivery_agent"
    system_prompt = (
        "You are the Delivery Agent in an e-commerce dispute pipeline. You "
        "are given verified order delivery timestamps already computed from "
        "the database. Write a 1-2 sentence handoff note stating whether the "
        "order was delivered to the customer after the estimated delivery "
        "date, or if it has not been delivered yet. Only use the facts given."
    )

    def run(self, case_id: str, store: DataStore, order_id: str) -> DeliveryFacts:
        order = store.get_order(order_id)
        if order is None:
            facts = DeliveryFacts(
                order_estimated_delivery_date=None,
                order_delivered_carrier_date=None,
                order_delivered_customer_date=None,
                delivered_after_estimate=None,
            )
            log_event(case_id, self.name, "tool_result", order_found=False, order_id=order_id)
            self.narrate(case_id, json.dumps({"order_found": False, "order_id": order_id}))
            return facts

        estimated = order["order_estimated_delivery_date"]
        delivered_customer = order["order_delivered_customer_date"]
        delivered_carrier = order["order_delivered_carrier_date"]

        if pd.notna(delivered_customer) and pd.notna(estimated):
            delivered_after_estimate = bool(delivered_customer > estimated)
        else:
            delivered_after_estimate = None

        facts = DeliveryFacts(
            order_estimated_delivery_date=estimated,
            order_delivered_carrier_date=delivered_carrier,
            order_delivered_customer_date=delivered_customer,
            delivered_after_estimate=delivered_after_estimate,
        )

        log_event(
            case_id,
            self.name,
            "tool_result",
            order_id=order_id,
            estimated_delivery_date=str(estimated),
            delivered_customer_date=str(delivered_customer),
            delivered_carrier_date=str(delivered_carrier),
            delivered_after_estimate=delivered_after_estimate,
        )
        self.narrate(
            case_id,
            json.dumps(
                {
                    "estimated_delivery_date": str(estimated),
                    "delivered_customer_date": str(delivered_customer),
                    "delivered_after_estimate": delivered_after_estimate,
                },
                ensure_ascii=False,
            ),
        )
        return facts
