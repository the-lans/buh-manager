import axios from 'axios'

const TOKEN_KEY = 'buh_token'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api/v1',
})

apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem(TOKEN_KEY)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}
