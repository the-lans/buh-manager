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


# Deduplication & algorithm constants
TX_DEDUP_WINDOW_SECONDS: int = 60

RECONCILE_PRE_WINDOW_HOURS: int = 12
RECONCILE_POST_WINDOW_DAYS: int = 3

SCORE_THRESHOLD_AUTO: int = 75

FUZZY_HIGH_THRESHOLD: int = 80
FUZZY_LOW_THRESHOLD: int = 50

SCORE_TIME_UNDER_1H: int = 40
SCORE_TIME_UNDER_12H: int = 25
SCORE_TIME_UNDER_3D: int = 10
SCORE_FUZZY_HIGH: int = 40
SCORE_FUZZY_LOW: int = 20
SCORE_SINGLE_PAIR_BONUS: int = 20

MEDIA_PATH: str = "media"
S3_ENDPOINT_URL: str = "https://storage.yandexcloud.net"

API_KEY_PREFIX: str = "bm_"
API_KEY_RANDOM_BYTES: int = 32
API_KEY_PREFIX_LENGTH: int = 8
