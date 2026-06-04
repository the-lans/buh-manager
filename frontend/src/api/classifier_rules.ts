import { apiClient } from './client'
import type { ClassifierRule, ClassifierRuleCreate, ClassifierRuleUpdate } from '../types'

export const classifierRulesApi = {
  list: () =>
    apiClient.get<ClassifierRule[]>('/classifier-rules').then((r) => r.data),
  create: (data: ClassifierRuleCreate) =>
    apiClient.post<ClassifierRule>('/classifier-rules', data).then((r) => r.data),
  update: (id: string, data: ClassifierRuleUpdate) =>
    apiClient.put<ClassifierRule>(`/classifier-rules/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/classifier-rules/${id}`),
  apply: (data: { start_date: string; end_date: string }) =>
    apiClient
      .post<{ updated_count: number }>('/classifier-rules/apply', data)
      .then((r) => r.data),
}
