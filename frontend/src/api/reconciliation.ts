import { apiClient } from './client'
import type { ReconciliationReport } from '../types'

export const reconciliationApi = {
  run: () => apiClient.post<ReconciliationReport>('/reconciliation/run').then((r) => r.data),
  getReport: () =>
    apiClient.get<ReconciliationReport | null>('/reconciliation/report').then((r) => r.data),
  match: (transaction_id: string, receipt_id: string) =>
    apiClient.post('/reconciliation/match', { transaction_id, receipt_id }).then((r) => r.data),
  ignore: (transaction_id: string) =>
    apiClient.post('/reconciliation/ignore', { transaction_id }).then((r) => r.data),
  resolveConflict: (transaction_id: string, action: 'KEEP_OLD' | 'UPDATE_FROM_NEW') =>
    apiClient
      .post('/reconciliation/resolve-conflict', { transaction_id, action })
      .then((r) => r.data),
}
