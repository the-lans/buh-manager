import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { setToken } from '../api/client'

export default function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    if (token) {
      setToken(token)
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
