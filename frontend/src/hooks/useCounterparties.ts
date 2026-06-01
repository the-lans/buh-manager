import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { counterpartiesApi } from '../api/counterparties'
import type { CounterpartyCreate, CounterpartyUpdate } from '../types'

const QUERY_KEY = 'counterparties'

export function useCounterparties() {
  return useQuery({ queryKey: [QUERY_KEY], queryFn: counterpartiesApi.list })
}

export function useCounterpartyMap(): Map<string, string> {
  const { data = [] } = useCounterparties()
  return new Map(data.map((cp) => [cp.id, cp.name]))
}

export function useCreateCounterparty() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CounterpartyCreate) => counterpartiesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  })
}

export function useUpdateCounterparty() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CounterpartyUpdate }) =>
      counterpartiesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  })
}

export function useDeleteCounterparty() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => counterpartiesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  })
}
