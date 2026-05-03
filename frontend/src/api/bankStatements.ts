import { apiClient } from './client'
import type { ImportReport } from '../types'

export const bankStatementsApi = {
  import: (data: object) =>
    apiClient.post<ImportReport>('/bank-statements', data).then((r) => r.data),
}
