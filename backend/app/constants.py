from decimal import Decimal
from enum import StrEnum


class DocumentType(StrEnum):
    RECEIPT = "RECEIPT"
    BANK_STATEMENT = "BANK_STATEMENT"


class DocumentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"


class CounterpartyType(StrEnum):
    STORE = "STORE"
    PERSON = "PERSON"
    COMPANY = "COMPANY"


class TransactionType(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class ReconciledStatus(StrEnum):
    UNMATCHED = "UNMATCHED"
    MATCHED = "MATCHED"
    NOT_REQUIRED = "NOT_REQUIRED"
    IGNORED_BY_USER = "IGNORED_BY_USER"


class ImportStatus(StrEnum):
    IMPORTED = "IMPORTED"
    DUPLICATE_SKIPPED = "DUPLICATE_SKIPPED"
    CONFLICT = "CONFLICT"


class BalanceSource(StrEnum):
    OPENING = "OPENING"
    CLOSING = "CLOSING"
    MANUAL = "MANUAL"


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MATCH = "MATCH"
    UNMATCH = "UNMATCH"
    IMPORT_CONFLICT = "IMPORT_CONFLICT"


class AuditEntityType(StrEnum):
    TRANSACTION = "transaction"
    RECEIPT = "receipt"
    MATCH = "match"
    IMPORT = "import"
    CLASSIFIER_RULE = "classifier_rule"


class ChangedBy(StrEnum):
    AGENT = "AGENT"
    USER = "USER"


class ConflictResolutionAction(StrEnum):
    KEEP_OLD = "KEEP_OLD"
    UPDATE_FROM_NEW = "UPDATE_FROM_NEW"


class ApiKeyScope(StrEnum):
    READ_DOCUMENTS = "read:documents"
    WRITE_DOCUMENTS = "write:documents"
    READ_RECEIPTS = "read:receipts"
    WRITE_RECEIPTS = "write:receipts"
    WRITE_BANK_STATEMENTS = "write:bank_statements"
    READ_TRANSACTIONS = "read:transactions"
    WRITE_TRANSACTIONS = "write:transactions"
    READ_RECONCILIATION = "read:reconciliation"
    WRITE_RECONCILIATION = "write:reconciliation"
    READ_ACCOUNTS = "read:accounts"
    WRITE_ACCOUNTS = "write:accounts"
    READ_EXPENSE_TYPES = "read:expense_types"
    WRITE_EXPENSE_TYPES = "write:expense_types"
    READ_COUNTERPARTIES = "read:counterparties"
    WRITE_COUNTERPARTIES = "write:counterparties"
    READ_EXCHANGE_RATES = "read:exchange_rates"
    WRITE_EXCHANGE_RATES = "write:exchange_rates"
    READ_AUDIT_LOG = "read:audit_log"
    READ_CLASSIFIER_RULES = "read:classifier_rules"
    WRITE_CLASSIFIER_RULES = "write:classifier_rules"
    READ_APP_CONSTANTS = "read:app_constants"
    WRITE_APP_CONSTANTS = "write:app_constants"


class ClassifierOp(StrEnum):
    EQ = "eq"
    LT = "lt"
    GT = "gt"
    LTE = "lte"
    GTE = "gte"
    BETWEEN = "between"


# Deduplication & algorithm constants
TX_DEDUP_WINDOW_SECONDS: int = 60

RECONCILE_PRE_WINDOW_HOURS: int = 12
RECONCILE_POST_WINDOW_DAYS: int = 3
RECONCILE_AMOUNT_TOLERANCE: Decimal = Decimal("0")
RECONCILE_AUTO_MATCH_MAX_HOURS: int = 12

MEDIA_PATH: str = "media"
S3_ENDPOINT_URL: str = "https://storage.yandexcloud.net"
MAX_UPLOAD_FILE_SIZE: int = 100 * 1024 * 1024
UPLOAD_READ_CHUNK_SIZE: int = 1024 * 1024

API_KEY_PREFIX: str = "bm_"
API_KEY_RANDOM_BYTES: int = 32
API_KEY_PREFIX_LENGTH: int = 8

DEFAULT_AUDIT_LOG_LIMIT: int = 50

RECEIPT_MAX_AGE_DAYS: int = 3650
