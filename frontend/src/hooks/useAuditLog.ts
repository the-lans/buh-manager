import { useQuery } from '@tanstack/react-query'

import { auditLogApi } from '../api/auditLog'
import type { AuditLogParams } from '../api/auditLog'

export function useAuditLog(params?: AuditLogParams) {
  return useQuery({
    queryKey: ['audit-log', params],
    queryFn: () => auditLogApi.list(params),
  })
}
