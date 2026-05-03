import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { expenseTypesApi } from '../api/expenseTypes'
import type { ExpenseType } from '../types'

export function useExpenseTypes() {
  return useQuery({ queryKey: ['expenseTypes'], queryFn: expenseTypesApi.list })
}

export function useCreateExpenseType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ExpenseType) => expenseTypesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['expenseTypes'] }),
  })
}

export function useUpdateExpenseType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ExpenseType> }) =>
      expenseTypesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['expenseTypes'] }),
  })
}

export function useDeleteExpenseType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => expenseTypesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['expenseTypes'] }),
  })
}
