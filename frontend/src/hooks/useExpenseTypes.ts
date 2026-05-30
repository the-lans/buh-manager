import { expenseTypesApi } from '../api/expenseTypes'
import type { ExpenseType } from '../types'
import { makeResourceHooks } from './makeResourceHooks'

const { useList, useCreate, useUpdate, useDelete } = makeResourceHooks<ExpenseType, ExpenseType, Partial<ExpenseType>>(
  'expenseTypes',
  expenseTypesApi,
)

export const useExpenseTypes = useList
export const useCreateExpenseType = useCreate
export const useUpdateExpenseType = useUpdate
export const useDeleteExpenseType = useDelete
