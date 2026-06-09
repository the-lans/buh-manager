import { apiClient } from './client'
import type { AppConstant } from '../types'

export const appConstantsApi = {
  list: () => apiClient.get<AppConstant[]>('/app-constants').then((r) => r.data),
  update: (key: string, value: string) =>
    apiClient.put<AppConstant>(`/app-constants/${key}`, { value }).then((r) => r.data),
}
