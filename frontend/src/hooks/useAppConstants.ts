import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { appConstantsApi } from '../api/appConstants'

export function useAppConstants() {
  return useQuery({ queryKey: ['app-constants'], queryFn: appConstantsApi.list })
}

export function useUpdateAppConstant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      appConstantsApi.update(key, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['app-constants'] }),
  })
}
