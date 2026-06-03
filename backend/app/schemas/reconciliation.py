from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_serializer, model_validator

from app.constants import ConflictResolutionAction
from app.utils.ids import unscope_user_id


class ReconciliationSummary(BaseModel):
    auto_matched_count: int
    missing_receipts_count: int
    unmatched_receipts_count: int
    collisions_count: int


class CollisionTransactionItem(BaseModel):
    id: UUID
    occurred_at: datetime
    amount: Decimal


class CollisionReceiptItem(BaseModel):
    id: UUID
    paid_at: datetime
    counterparty_id: str | None
    total_amount: Decimal

    @field_serializer("counterparty_id")
    def serialize_counterparty_id(self, value: str | None) -> str | None:
        return unscope_user_id(value)


class CollisionGroup(BaseModel):
    collision_id: str
    amount: Decimal
    reason: str
    message: str
    involved_transactions: list[CollisionTransactionItem]
    involved_receipts: list[CollisionReceiptItem]


class MissingReceiptItem(BaseModel):
    transaction_id: UUID
    occurred_at: datetime
    amount: Decimal
    expense_type_id: str | None

    @field_serializer("expense_type_id")
    def serialize_reference_ids(self, value: str | None) -> str | None:
        return unscope_user_id(value)


class UnmatchedReceiptItem(BaseModel):
    receipt_id: UUID
    paid_at: datetime
    total_amount: Decimal
    counterparty_id: str | None

    @field_serializer("counterparty_id")
    def serialize_counterparty_id(self, value: str | None) -> str | None:
        return unscope_user_id(value)


class ReconciliationReport(BaseModel):
    report_generated_at: datetime
    summary: ReconciliationSummary
    collisions: list[CollisionGroup]
    missing_receipts: list[MissingReceiptItem]
    unmatched_receipts: list[UnmatchedReceiptItem]


class ManualMatchRequest(BaseModel):
    transaction_id: UUID
    receipt_id: UUID


class IgnoreRequest(BaseModel):
    transaction_id: UUID


class ResolveConflictRequest(BaseModel):
    transaction_id: UUID
    action: ConflictResolutionAction
    incoming_amount: Decimal | None = None

    @model_validator(mode="after")
    def validate_update_payload(self) -> "ResolveConflictRequest":
        if self.action == ConflictResolutionAction.UPDATE_FROM_NEW and self.incoming_amount is None:
            raise ValueError("incoming_amount is required for UPDATE_FROM_NEW.")
        return self
