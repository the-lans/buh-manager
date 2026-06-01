import type { AuditLogEntry } from '../types'
import { apiClient } from './client'

export interface AuditLogParams {
  entity_type?: string
  skip?: number
  limit?: number
}

export const auditLogApi = {
  list: (params?: AuditLogParams) =>
    apiClient.get<AuditLogEntry[]>('/audit-log', { params }).then((r) => r.data),
}
