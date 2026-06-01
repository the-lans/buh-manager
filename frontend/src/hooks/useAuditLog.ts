import { useQuery } from '@tanstack/react-query'

import { AuditLogParams, auditLogApi } from '../api/auditLog'

export function useAuditLog(params?: AuditLogParams) {
  return useQuery({
    queryKey: ['audit-log', params],
    queryFn: () => auditLogApi.list(params),
  })
}
