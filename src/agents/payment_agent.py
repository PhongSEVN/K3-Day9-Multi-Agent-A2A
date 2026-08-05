"""Payment Agent: reconciles payment rows against item + freight totals."""
from __future__ import annotations

import json

import pandas as pd

from ..data_store import DataStore
from ..logger import log_event
from ..policy_rules import PaymentFact, PaymentFacts
from .base_agent import BaseAgent


class PaymentAgent(BaseAgent):
    name = "payment_agent"
    system_prompt = (
        "You are the Payment Agent in an e-commerce dispute pipeline. You are "
        "given verified payment rows and the item+freight total already "
        "computed from the database. Write a 1-2 sentence handoff note on "
        "whether the payments reconcile with the order total. Only use the "
        "facts given; never invent a transaction or refund event."
    )

    def run(
        self,
        case_id: str,
        store: DataStore,
        order_id: str,
        item_total: float,
        freight_total: float,
    ) -> PaymentFacts:
        payments_df = store.get_payments(order_id)

        payments: list[PaymentFact] = []
        payment_total = 0.0
        for _, row in payments_df.iterrows():
            value = float(row["payment_value"]) if pd.notna(row["payment_value"]) else 0.0
            payment_total += value
            payments.append(
                PaymentFact(
                    payment_sequential=int(row["payment_sequential"]),
                    payment_type=str(row["payment_type"]),
                    payment_value=round(value, 2),
                )
            )

        facts = PaymentFacts(payments=payments, payment_total=round(payment_total, 2))

        log_event(
            case_id,
            self.name,
            "tool_result",
            order_id=order_id,
            payment_count=facts.payment_count,
            payment_total=facts.payment_total,
            expected_total=round(item_total + freight_total, 2),
        )
        self.narrate(
            case_id,
            json.dumps(
                {
                    "payment_count": facts.payment_count,
                    "payment_total": facts.payment_total,
                    "expected_total": round(item_total + freight_total, 2),
                }
            ),
        )
        return facts
