import { useQuery } from '@tanstack/react-query'
import { accountsApi } from '../api/accounts'
import type { Account, AccountCreate, AccountUpdate } from '../types'
import { makeResourceHooks } from './makeResourceHooks'

const { useList, useCreate, useUpdate, useDelete } = makeResourceHooks<Account, AccountCreate, AccountUpdate>(
  'accounts',
  accountsApi,
)

export const useAccounts = useList
export const useCreateAccount = useCreate
export const useUpdateAccount = useUpdate
export const useDeleteAccount = useDelete

export function useAccountsLazy(enabled: boolean) {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: accountsApi.list,
    enabled,
  })
}
