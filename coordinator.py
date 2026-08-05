"""Coordinator for the six-agent Olist dispute-resolution workflow."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from delivery_agent import DeliveryAgent
from model_config import MODEL_NAME, MODEL_PARAMETER_SIZE
from order_seller_agent import OrderSellerAgent
from payment_agent import PaymentAgent
from policy_agent import PolicyAgent
from verifier_agent import VerifierAgent


class Coordinator:
    def __init__(self, data_dir: Path | str = "data") -> None:
        self.order_agent = OrderSellerAgent(data_dir)
        self.payment_agent = PaymentAgent(data_dir)
        self.delivery_agent = DeliveryAgent(data_dir)
        self.policy_agent = PolicyAgent()
        self.verifier_agent = VerifierAgent(data_dir)

    @staticmethod
    def _trace(stream, agent: str, event: str, case_id: str, payload: dict) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "event": event,
            "case_id": case_id,
            "payload": payload,
        }
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def process_case(self, case: dict, trace_stream) -> dict:
        case_id = case["case_id"]
        order_id = case["customer_request"]["claimed_order_id"]
        if case.get("policy_version") != PolicyAgent.POLICY_VERSION:
            raise ValueError(f"Unsupported policy for {case_id}")

        self._trace(trace_stream, "coordinator", "case_received", case_id, {"order_id": order_id})
        order = self.order_agent.investigate(case_id, order_id)
        self._trace(trace_stream, "order_seller_agent", "handoff", case_id, asdict(order))
        payment = self.payment_agent.investigate(case_id, order_id)
        self._trace(trace_stream, "payment_agent", "handoff", case_id, asdict(payment))
        delivery = self.delivery_agent.investigate(case_id, order_id)
        self._trace(trace_stream, "delivery_agent", "handoff", case_id, asdict(delivery))
        decision = self.policy_agent.decide(order, payment, delivery)
        self._trace(trace_stream, "policy_agent", "handoff", case_id, asdict(decision))

        # Affected sellers and evidence are issue-aware. A seller is related to
        # an order, but is only an affected entity when EC_POLICY_V1 assigns
        # seller responsibility. Likewise, canceled/unavailable decisions need
        # order/payment evidence, not unrelated item/seller rows.
        affected_seller_ids = (
            delivery.violating_seller_ids[:5]
            if decision.primary_issue == "late_delivery_seller"
            else []
        )
        item_evidence = (
            []
            if decision.primary_issue in {"canceled_order_paid", "unavailable_order_paid"}
            else order.item_evidence_ids
        )
        seller_evidence = (
            [f"seller:{seller_id}" for seller_id in affected_seller_ids]
            if decision.primary_issue == "late_delivery_seller"
            else []
        )
        evidence = list(
            dict.fromkeys(
                [order.order_evidence_id]
                + item_evidence
                + payment.payment_evidence_ids
                + seller_evidence
                + [f"policy:{decision.root_cause_code}"]
            )
        )[:10]
        output = {
            "case_id": case_id,
            "assessment": {
                "primary_issue": decision.primary_issue,
                "case_status": decision.case_status,
                "confidence": decision.confidence,
            },
            "affected_entities": {
                "order_ids": [order_id],
                "item_ids": order.item_ids,
                "seller_ids": affected_seller_ids,
                "payment_ids": payment.payment_ids,
            },
            "root_cause_analysis": {
                "ranked_causes": [{"cause_code": decision.root_cause_code, "rank": 1}],
                "responsible_parties": decision.responsible_parties,
            },
            "evidence_ids": evidence,
            "financial_resolution": {
                "currency": "BRL",
                "item_total_brl": order.item_total_brl,
                "freight_total_brl": order.freight_total_brl,
                "payment_total_brl": payment.payment_total_brl,
                "recommended_refund_brl": round(decision.recommended_refund_brl, 2),
            },
            "resolution_actions": decision.resolution_actions,
        }
        self.verifier_agent.verify(output, case_id)
        self._trace(trace_stream, "verifier_agent", "approved", case_id, {"evidence_count": len(evidence)})
        return output

    def run(
        self,
        input_dir: Path | str = "input",
        output_dir: Path | str = "output",
        trace_path: Path | str = "logging/trace.jsonl",
    ) -> int:
        input_dir, output_dir, trace_path = Path(input_dir), Path(output_dir), Path(trace_path)
        cases = sorted(input_dir.glob("EC_*.json"))
        expected = {f"EC_{number:03d}.json" for number in range(1, 51)}
        actual = {path.name for path in cases}
        if actual != expected:
            raise ValueError(f"Expected EC_001..EC_050; missing={sorted(expected-actual)}")

        output_dir.mkdir(parents=True, exist_ok=True)
        for old_output in output_dir.glob("EC_*.json"):
            old_output.unlink()
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", encoding="utf-8") as trace_stream:
            for case_path in cases:
                case = json.loads(case_path.read_text(encoding="utf-8-sig"))
                output = self.process_case(case, trace_stream)
                target = output_dir / case_path.name
                target.write_text(
                    json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                self._trace(trace_stream, "coordinator", "output_written", case["case_id"], {"path": str(target)})
        return len(cases)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all agents for 50 Olist cases")
    parser.add_argument("--input-dir", default="input")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--trace", default="logging/trace.jsonl")
    args = parser.parse_args()
    count = Coordinator(args.data_dir).run(args.input_dir, args.output_dir, args.trace)
    print(f"Multi-agent pipeline wrote and verified {count} output files")


if __name__ == "__main__":
    main()
