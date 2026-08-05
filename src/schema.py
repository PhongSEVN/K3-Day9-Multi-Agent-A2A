"""Pydantic models mirroring the required output/EC_XXX.json schema.

Used by VerifierAgent as the final structural gate before a case is
written to output/.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .config import (
    MAX_ENTITY_IDS,
    MAX_EVIDENCE_IDS,
    MAX_ROOT_CAUSES,
    MAX_RESPONSIBLE_PARTIES,
    MAX_RESOLUTION_ACTIONS,
)

PrimaryIssue = Literal[
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
]


class Assessment(BaseModel):
    primary_issue: PrimaryIssue
    case_status: Literal["action_required", "no_action"]
    confidence: float = Field(ge=0.0, le=1.0)


class AffectedEntities(BaseModel):
    order_ids: list[str] = Field(default_factory=list, max_length=MAX_ENTITY_IDS)
    item_ids: list[str] = Field(default_factory=list, max_length=MAX_ENTITY_IDS)
    seller_ids: list[str] = Field(default_factory=list, max_length=MAX_ENTITY_IDS)
    payment_ids: list[str] = Field(default_factory=list, max_length=MAX_ENTITY_IDS)


class RankedCause(BaseModel):
    cause_code: str
    rank: int


class ResponsibleParty(BaseModel):
    party_type: str
    party_id: str


class RootCauseAnalysis(BaseModel):
    ranked_causes: list[RankedCause] = Field(default_factory=list, max_length=MAX_ROOT_CAUSES)
    responsible_parties: list[ResponsibleParty] = Field(
        default_factory=list, max_length=MAX_RESPONSIBLE_PARTIES
    )


class FinancialResolution(BaseModel):
    currency: str
    item_total_brl: float
    freight_total_brl: float
    payment_total_brl: float
    recommended_refund_brl: float


class CaseOutput(BaseModel):
    case_id: str
    assessment: Assessment
    affected_entities: AffectedEntities
    root_cause_analysis: RootCauseAnalysis
    evidence_ids: list[str] = Field(default_factory=list, max_length=MAX_EVIDENCE_IDS)
    financial_resolution: FinancialResolution
    resolution_actions: list[str] = Field(default_factory=list, max_length=MAX_RESOLUTION_ACTIONS)
