import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { balancesApi } from '../api/balances'

export function useBalances(params?: { account_id?: string; skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['balances', params],
    queryFn: () => balancesApi.list(params),
  })
}

export function useCalculateBalances() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: balancesApi.calculate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['balances'] }),
  })
}
