import { apiKeysApi } from '../api/apiKeys'
import type { ApiKey, ApiKeyCreate, ApiKeyCreated, ApiKeyUpdate } from '../types'
import { makeResourceHooks } from './makeResourceHooks'

const { useList, useCreate, useUpdate, useDelete } = makeResourceHooks<ApiKey, ApiKeyCreate, ApiKeyUpdate, ApiKeyCreated>(
  'api-keys',
  apiKeysApi,
)

export const useApiKeys = useList
export const useCreateApiKey = useCreate
export const useUpdateApiKey = useUpdate
export const useDeleteApiKey = useDelete
