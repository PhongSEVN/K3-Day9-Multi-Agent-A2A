"""Strict output/evidence verifier used before any case file is written."""

from __future__ import annotations

import csv
from pathlib import Path

from model_config import MODEL_NAME, MODEL_PARAMETER_SIZE


class VerificationError(ValueError):
    pass


class VerifierAgent:
    TOP_LEVEL_KEYS = {
        "case_id",
        "assessment",
        "affected_entities",
        "root_cause_analysis",
        "evidence_ids",
        "financial_resolution",
        "resolution_actions",
    }
    CAUSES = {
        "SELLER_HANDOFF_AFTER_LIMIT",
        "CARRIER_DELIVERED_AFTER_ESTIMATE",
        "ORDER_CANCELED_AFTER_PAYMENT",
        "ORDER_UNAVAILABLE_AFTER_PAYMENT",
        "MULTIPLE_PAYMENTS_RECONCILED",
        "DELIVERY_WITHIN_ESTIMATE",
    }

    def __init__(self, data_dir: Path | str = "data") -> None:
        data_dir = Path(data_dir)
        self.orders = self._column(data_dir / "olist_orders_dataset.csv", "order_id")
        self.sellers = self._column(data_dir / "olist_sellers_dataset.csv", "seller_id")
        self.items: set[str] = set()
        self.payments: set[str] = set()
        with (data_dir / "olist_order_items_dataset.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            for row in csv.DictReader(stream):
                self.items.add(f'{row["order_id"]}:{row["order_item_id"]}')
        with (data_dir / "olist_order_payments_dataset.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            for row in csv.DictReader(stream):
                self.payments.add(f'{row["order_id"]}:{row["payment_sequential"]}')

    @staticmethod
    def _column(path: Path, column: str) -> set[str]:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return {row[column] for row in csv.DictReader(stream)}

    def verify(self, output: dict, expected_case_id: str) -> None:
        errors: list[str] = []
        if set(output) != self.TOP_LEVEL_KEYS:
            errors.append("top-level schema keys do not match")
        if output.get("case_id") != expected_case_id:
            errors.append("case_id does not match input")

        assessment = output.get("assessment", {})
        confidence = assessment.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            errors.append("confidence must be within [0, 1]")
        if assessment.get("case_status") not in {"action_required", "no_action"}:
            errors.append("invalid case_status")

        entities = output.get("affected_entities", {})
        limits = {"order_ids": 5, "item_ids": 5, "seller_ids": 5, "payment_ids": 5}
        valid_sets = {
            "order_ids": self.orders,
            "item_ids": self.items,
            "seller_ids": self.sellers,
            "payment_ids": self.payments,
        }
        for key, limit in limits.items():
            values = entities.get(key, [])
            if not isinstance(values, list) or len(values) > limit:
                errors.append(f"{key} exceeds schema limit")
                continue
            if any(value not in valid_sets[key] for value in values):
                errors.append(f"{key} contains an unknown ID")

        evidence = output.get("evidence_ids", [])
        if not isinstance(evidence, list) or len(evidence) > 10:
            errors.append("evidence_ids exceeds schema limit")
        else:
            for evidence_id in evidence:
                if not self._valid_evidence(evidence_id):
                    errors.append(f"invalid evidence ID: {evidence_id}")

        analysis = output.get("root_cause_analysis", {})
        causes = analysis.get("ranked_causes", [])
        parties = analysis.get("responsible_parties", [])
        actions = output.get("resolution_actions", [])
        if not 1 <= len(causes) <= 3 or causes[0].get("rank") != 1:
            errors.append("ranked_causes must start at rank 1")
        if any(cause.get("cause_code") not in self.CAUSES for cause in causes):
            errors.append("unknown root cause")
        if len(parties) > 3:
            errors.append("too many responsible parties")
        if not 1 <= len(actions) <= 5:
            errors.append("invalid resolution action count")

        issue = assessment.get("primary_issue")
        seller_entities = entities.get("seller_ids", [])
        seller_evidence = [value[7:] for value in evidence if value.startswith("seller:")]
        item_evidence = [value[5:] for value in evidence if value.startswith("item:")]
        if issue == "late_delivery_seller":
            responsible_sellers = [
                party.get("party_id")
                for party in parties
                if party.get("party_type") == "seller"
            ]
            if set(seller_entities) != set(responsible_sellers):
                errors.append("affected sellers must equal responsible sellers")
            if set(seller_evidence) != set(seller_entities):
                errors.append("seller evidence must cover affected sellers")
        elif seller_entities or seller_evidence:
            errors.append("seller entity/evidence is not relevant to this primary issue")

        if issue in {"canceled_order_paid", "unavailable_order_paid"} and item_evidence:
            errors.append("canceled/unavailable decisions must not include item evidence")
        if causes and not any(
            value == f"policy:{causes[0].get('cause_code')}" for value in evidence
        ):
            errors.append("policy evidence must match rank-1 root cause")
        order_entities = entities.get("order_ids", [])
        if not all(f"order:{order_id}" in evidence for order_id in order_entities):
            errors.append("order evidence must cover affected orders")
        payment_entities = entities.get("payment_ids", [])
        if not all(f"payment:{payment_id}" in evidence for payment_id in payment_entities):
            errors.append("payment evidence must cover affected payments")

        financial = output.get("financial_resolution", {})
        if financial.get("currency") != "BRL":
            errors.append("currency must be BRL")
        for key in (
            "item_total_brl",
            "freight_total_brl",
            "payment_total_brl",
            "recommended_refund_brl",
        ):
            value = financial.get(key)
            if not isinstance(value, (int, float)) or round(value, 2) != value or value < 0:
                errors.append(f"invalid monetary value: {key}")
        expected_status = (
            "action_required" if financial.get("recommended_refund_brl", 0) > 0 else "no_action"
        )
        if assessment.get("case_status") != expected_status:
            errors.append("case_status disagrees with refund")

        if errors:
            raise VerificationError("; ".join(errors))

    def _valid_evidence(self, evidence_id: str) -> bool:
        if evidence_id.startswith("order:"):
            return evidence_id[6:] in self.orders
        if evidence_id.startswith("item:"):
            return evidence_id[5:] in self.items
        if evidence_id.startswith("payment:"):
            return evidence_id[8:] in self.payments
        if evidence_id.startswith("seller:"):
            return evidence_id[7:] in self.sellers
        if evidence_id.startswith("policy:"):
            return evidence_id[7:] in self.CAUSES
        return False
