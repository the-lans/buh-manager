import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

interface ResourceApi<TItem, TCreate, TUpdate, TCreated = TItem> {
  list: () => Promise<TItem[]>
  create: (data: TCreate) => Promise<TCreated>
  update: (id: string, data: TUpdate) => Promise<TItem>
  delete: (id: string) => Promise<unknown>
}

export function makeResourceHooks<TItem, TCreate, TUpdate, TCreated = TItem>(
  queryKey: string,
  api: ResourceApi<TItem, TCreate, TUpdate, TCreated>,
) {
  function useList() {
    return useQuery({ queryKey: [queryKey], queryFn: api.list })
  }

  function useCreate() {
    const qc = useQueryClient()
    return useMutation({
      mutationFn: (data: TCreate) => api.create(data),
      onSuccess: () => qc.invalidateQueries({ queryKey: [queryKey] }),
    })
  }

  function useUpdate() {
    const qc = useQueryClient()
    return useMutation({
      mutationFn: ({ id, data }: { id: string; data: TUpdate }) => api.update(id, data),
      onSuccess: () => qc.invalidateQueries({ queryKey: [queryKey] }),
    })
  }

  function useDelete() {
    const qc = useQueryClient()
    return useMutation({
      mutationFn: (id: string) => api.delete(id),
      onSuccess: () => qc.invalidateQueries({ queryKey: [queryKey] }),
    })
  }

  return { useList, useCreate, useUpdate, useDelete }
}
