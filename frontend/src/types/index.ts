export interface User {
  id: string
  email: string
  full_name: string | null
  avatar_url: string | null
  is_active: boolean
}

export interface Account {
  id: string
  user_id: string
  bank: string
  account_number: string
  currency: string
  is_active: boolean
  has_balances: boolean
}

export interface AccountCreate {
  bank: string
  account_number: string
  currency?: string
}

export interface AccountUpdate {
  bank?: string
  account_number?: string
  currency?: string
  is_active?: boolean
}

export interface Document {
  id: string
  user_id: string
  type: 'BANK_STATEMENT' | 'RECEIPT'
  url: string
  name: string
  status: 'PENDING' | 'PROCESSED' | 'ERROR'
  email_source: string | null
  file_hash: string
  uploaded_at: string
  payload?: Record<string, unknown> | null
  raw_parsed_data?: string | null
}

export interface ReceiptItem {
  id: string
  code: string | null
  name: string
  unit: string | null
  quantity: string
  price: string
  amount: string
  tags: string[] | null
}

export interface Receipt {
  id: string
  document_id: string | null
  paid_at: string
  total_amount: string
  counterparty_id: string | null
  fn: string | null
  fd: string | null
  fpd: string | null
  items: ReceiptItem[]
}

export interface ReceiptListItem {
  id: string
  paid_at: string
  total_amount: string
  counterparty_id: string | null
  document_id: string | null
}

export interface Transaction {
  id: string
  account_id: string
  occurred_at: string
  processed_at: string | null
  amount: string
  type: 'INCOME' | 'EXPENSE' | 'TRANSFER'
  bank_category: string | null
  expense_type_id: string
  description: string | null
  balance_after: string | null
  calculated_balance_after: string | null
  balance_mismatch: boolean
  receipt_id: string | null
  reconciled_status: 'UNMATCHED' | 'MATCHED' | 'NOT_REQUIRED' | 'IGNORED_BY_USER'
  import_status: 'IMPORTED' | 'DUPLICATE_SKIPPED' | 'CONFLICT'
  document_id: string | null
}

export interface ExpenseType {
  id: string
  name: string
  description: string | null
  receipt_required: boolean
}

export interface Counterparty {
  id: string
  name: string
  type: string
  inn: string | null
  kpp: string | null
  payload?: Record<string, unknown> | null
}

export interface CounterpartyCreate {
  name: string
  type?: string
  inn?: string | null
  kpp?: string | null
  payload?: Record<string, unknown> | null
}

export interface CounterpartyUpdate {
  name?: string
  type?: string
  inn?: string | null
  kpp?: string | null
  payload?: Record<string, unknown> | null
}

export interface AuditLogEntry {
  id: string
  entity_type: string
  entity_id: string
  action: string
  changed_by: string
  changed_at: string
  diff: string | null
}

export interface ExchangeRate {
  id: string
  base_currency: string
  quote_currency: string
  rate: string
  recorded_at: string
}

export interface ImportSummary {
  imported_count: number
  duplicate_count: number
  conflict_count: number
}

export interface BalanceCheck {
  is_available: boolean
  opening_balance_statement: string | null
  closing_balance_statement: string | null
  closing_balance_calculated: string | null
  is_consistent: boolean | null
  discrepancy: string | null
}

export interface ConflictItem {
  transaction_id: string
  occurred_at: string
  existing_amount: string
  incoming_amount: string
}

export interface ImportReport {
  document_id: string
  account_id: string
  period: { start: string; end: string }
  summary: ImportSummary
  balance_check: BalanceCheck
  conflicts: ConflictItem[]
  imported_transaction_ids: string[]
  is_initial_import: boolean
  opening_balance_missing: boolean
}

export interface ReconciliationSummary {
  auto_matched_count: number
  missing_receipts_count: number
  unmatched_receipts_count: number
  collisions_count: number
}

export interface MissingReceiptItem {
  transaction_id: string
  occurred_at: string
  amount: string
  expense_type_id: string | null
}

export interface UnmatchedReceiptItem {
  receipt_id: string
  paid_at: string
  total_amount: string
  counterparty_id: string | null
}

export interface CollisionGroup {
  collision_id: string
  amount: string
  reason: string
  message: string
  involved_transactions: { id: string; occurred_at: string; amount: string }[]
  involved_receipts: { id: string; paid_at: string; counterparty_id: string | null; total_amount: string }[]
}

export interface ReconciliationReport {
  report_generated_at: string
  summary: ReconciliationSummary
  collisions: CollisionGroup[]
  missing_receipts: MissingReceiptItem[]
  unmatched_receipts: UnmatchedReceiptItem[]
}

export interface Balance {
  id: string
  account_id: string
  amount: string
  recorded_at: string
  source: 'OPENING' | 'CLOSING' | 'MANUAL'
  document_id: string | null
}

export interface LinkResult {
  document_id: string
  status: string
  updated_count: number
  message: string | null
}

export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  scopes: string[]
  is_active: boolean
  created_at: string
  last_used_at: string | null
  expires_at: string | null
}

export interface ApiKeyCreated extends ApiKey {
  key: string
}

export interface ApiKeyCreate {
  name: string
  scopes: string[]
  expires_at?: string | null
}

export interface ApiKeyUpdate {
  name?: string
  scopes?: string[]
  is_active?: boolean
}
