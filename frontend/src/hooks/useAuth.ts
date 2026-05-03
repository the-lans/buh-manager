import { jwtDecode } from 'jwt-decode'
import { getToken, clearToken } from '../api/client'

interface JwtPayload {
  sub: string
  email: string
  exp: number
}

export function useAuth() {
  const token = getToken()

  if (!token) {
    return { user: null, isAuthenticated: false, logout }
  }

  try {
    const payload = jwtDecode<JwtPayload>(token)
    const isExpired = payload.exp * 1000 < Date.now()

    if (isExpired) {
      clearToken()
      return { user: null, isAuthenticated: false, logout }
    }

    return {
      user: { id: payload.sub, email: payload.email },
      isAuthenticated: true,
      logout,
    }
  } catch {
    clearToken()
    return { user: null, isAuthenticated: false, logout }
  }
}

function logout(): void {
  clearToken()
  window.location.href = '/login'
}
