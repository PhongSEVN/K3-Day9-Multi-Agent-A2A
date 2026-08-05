"""EC_POLICY_V1 specialist that turns verified domain handoffs into a draft."""

from __future__ import annotations

from dataclasses import dataclass

from delivery_agent import DeliveryHandoff
from model_config import MODEL_NAME, MODEL_PARAMETER_SIZE
from order_seller_agent import OrderSellerHandoff
from payment_agent import PaymentHandoff


@dataclass(frozen=True)
class PolicyDecision:
    primary_issue: str
    root_cause_code: str
    case_status: str
    confidence: float
    responsible_parties: list[dict[str, str]]
    recommended_refund_brl: float
    resolution_actions: list[str]


class PolicyAgent:
    """Apply EC_POLICY_V1 in its mandatory priority order."""

    POLICY_VERSION = "EC_POLICY_V1"
    CONFIDENCE_BY_ISSUE = {
        "canceled_order_paid": 0.95,
        "unavailable_order_paid": 0.95,
        "late_delivery_seller": 0.92,
        "late_delivery_logistics": 0.90,
        "valid_split_payment": 0.88,
        "unsupported_late_claim": 0.85,
    }

    def decide(
        self,
        order: OrderSellerHandoff,
        payment: PaymentHandoff,
        delivery: DeliveryHandoff,
    ) -> PolicyDecision:
        if order.order_status == "canceled" and payment.payment_total_brl > 0:
            return self._decision(
                "canceled_order_paid",
                "ORDER_CANCELED_AFTER_PAYMENT",
                "platform",
                "OLIST_PLATFORM",
                payment.payment_total_brl,
                "issue_full_refund",
            )
        if order.order_status == "unavailable" and payment.payment_total_brl > 0:
            return self._decision(
                "unavailable_order_paid",
                "ORDER_UNAVAILABLE_AFTER_PAYMENT",
                "platform",
                "OLIST_PLATFORM",
                payment.payment_total_brl,
                "issue_full_refund",
            )
        if delivery.delivered_late is True and delivery.violating_seller_ids:
            parties = [
                {"party_type": "seller", "party_id": seller_id}
                for seller_id in delivery.violating_seller_ids[:3]
            ]
            return PolicyDecision(
                primary_issue="late_delivery_seller",
                root_cause_code="SELLER_HANDOFF_AFTER_LIMIT",
                case_status="action_required",
                confidence=self.CONFIDENCE_BY_ISSUE["late_delivery_seller"],
                responsible_parties=parties,
                recommended_refund_brl=order.freight_total_brl,
                resolution_actions=["refund_freight"],
            )
        if delivery.delivered_late is True:
            return self._decision(
                "late_delivery_logistics",
                "CARRIER_DELIVERED_AFTER_ESTIMATE",
                "logistics_provider",
                "LOGISTICS_PROVIDER",
                order.freight_total_brl,
                "refund_freight",
            )
        if payment.payment_row_count >= 2 and payment.reconciled_within_010_brl:
            return PolicyDecision(
                primary_issue="valid_split_payment",
                root_cause_code="MULTIPLE_PAYMENTS_RECONCILED",
                case_status="no_action",
                confidence=self.CONFIDENCE_BY_ISSUE["valid_split_payment"],
                responsible_parties=[],
                recommended_refund_brl=0.0,
                resolution_actions=["explain_valid_split_payment"],
            )
        if delivery.delivered_late is False and payment.reconciled_within_010_brl:
            return PolicyDecision(
                primary_issue="unsupported_late_claim",
                root_cause_code="DELIVERY_WITHIN_ESTIMATE",
                case_status="no_action",
                confidence=self.CONFIDENCE_BY_ISSUE["unsupported_late_claim"],
                responsible_parties=[],
                recommended_refund_brl=0.0,
                resolution_actions=["reject_late_refund"],
            )
        raise ValueError(f"No EC_POLICY_V1 rule matched order {order.order_id}")

    @classmethod
    def _decision(
        cls,
        issue: str,
        cause: str,
        party_type: str,
        party_id: str,
        refund: float,
        action: str,
    ) -> PolicyDecision:
        return PolicyDecision(
            primary_issue=issue,
            root_cause_code=cause,
            case_status="action_required",
            confidence=cls.CONFIDENCE_BY_ISSUE[issue],
            responsible_parties=[{"party_type": party_type, "party_id": party_id}],
            recommended_refund_brl=round(refund, 2),
            resolution_actions=[action],
        )
