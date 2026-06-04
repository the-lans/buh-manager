import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { classifierRulesApi } from '../api/classifier_rules'
import type { ClassifierRuleCreate, ClassifierRuleUpdate } from '../types'

const QUERY_KEY = 'classifier-rules'

export function useClassifierRules() {
  return useQuery({ queryKey: [QUERY_KEY], queryFn: classifierRulesApi.list })
}

export function useCreateClassifierRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ClassifierRuleCreate) => classifierRulesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  })
}

export function useUpdateClassifierRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ClassifierRuleUpdate }) =>
      classifierRulesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  })
}

export function useDeleteClassifierRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => classifierRulesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  })
}

export function useApplyClassifierRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { start_date: string; end_date: string }) =>
      classifierRulesApi.apply(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })
}
