from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class BankStatementTransactionIn(BaseModel):
    occurred_at: datetime
    processed_at: datetime | None = None
    auth_code: str | None = None
    amount: Decimal
    type: str
    bank_category: str | None = None
    counterparty_name: str | None = None
    description: str | None = None
    balance_after: Decimal | None = None


class BankStatementCreate(BaseModel):
    document_id: UUID
    account_id: UUID
    statement_start: datetime
    statement_end: datetime
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    transactions: list[BankStatementTransactionIn]


class ImportSummary(BaseModel):
    imported_count: int
    duplicate_count: int
    conflict_count: int


class BalanceCheck(BaseModel):
    is_available: bool = True
    opening_balance_statement: Decimal | None
    closing_balance_statement: Decimal | None
    closing_balance_calculated: Decimal | None = None
    is_consistent: bool | None = None
    discrepancy: Decimal | None = None


class ConflictItem(BaseModel):
    transaction_id: UUID
    occurred_at: datetime
    existing_amount: Decimal
    incoming_amount: Decimal


class ImportReport(BaseModel):
    document_id: UUID
    account_id: UUID
    period: dict[str, str]
    summary: ImportSummary
    balance_check: BalanceCheck
    conflicts: list[ConflictItem]
    imported_transaction_ids: list[UUID]
    is_initial_import: bool = False
    opening_balance_missing: bool = False
