import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { setToken } from '../api/client'

export default function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const fragment = window.location.hash.startsWith('#')
      ? window.location.hash.slice(1)
      : window.location.hash
    const hashParams = new URLSearchParams(fragment)
    const token = hashParams.get('token') ?? params.get('token')
    if (token) {
      setToken(token)
      window.history.replaceState(null, '', window.location.pathname)
      navigate('/', { replace: true })
    } else {
      navigate('/login', { replace: true })
    }
  }, [navigate])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-gray-500">Выполняется вход...</div>
    </div>
  )
}
