import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const [loginName, setLoginName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(loginName, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-primary-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-bold text-center text-gray-800 mb-2">
          小伴 · 配置者端
        </h1>
        <p className="text-sm text-center text-gray-500 mb-8">
          请输入用户名和密码以继续
        </p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <input
              type="text"
              value={loginName}
              onChange={(e) => setLoginName(e.target.value)}
              placeholder="用户名"
              className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
              autoFocus
              autoComplete="username"
            />
          </div>
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="密码"
              className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
              autoComplete="current-password"
            />
          </div>

          {error && (
            <p className="text-red-500 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !loginName || !password}
            className="w-full py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '验证中...' : '进入配置'}
          </button>
        </form>
      </div>
    </div>
  )
}
