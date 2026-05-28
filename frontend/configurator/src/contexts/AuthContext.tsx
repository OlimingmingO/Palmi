import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface AuthContextType {
  isAuthenticated: boolean
  login: (login_name: string, password: string) => Promise<void>
  logout: () => void
  getAuthHeader: () => Record<string, string>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => !!localStorage.getItem('config_token')
  )

  const login = useCallback(async (login_name: string, password: string) => {
    const res = await fetch('/api/configurator/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login_name, password }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => null)
      throw new Error(data?.detail || '用户名或密码错误')
    }
    const data = await res.json()
    if (!data?.token) {
      throw new Error('登录响应缺少 token')
    }
    localStorage.setItem('config_token', data.token)
    setIsAuthenticated(true)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('config_token')
    setIsAuthenticated(false)
  }, [])

  const getAuthHeader = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('config_token')
    if (token) return { Authorization: `Bearer ${token}` }
    return {}
  }, [])

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, getAuthHeader }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
