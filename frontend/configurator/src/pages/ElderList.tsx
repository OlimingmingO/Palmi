import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { apiGet } from '../api/client'

interface ElderItem {
  elder_id: string
  nickname: string | null
  status: string
  created_at: string
  profile_version: number | null
}

const statusLabels: Record<string, string> = {
  active: '活跃',
  silent: '沉默',
  at_risk: '流失风险',
  new: '新用户',
}

const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  silent: 'bg-yellow-100 text-yellow-700',
  at_risk: 'bg-red-100 text-red-700',
  new: 'bg-blue-100 text-blue-700',
}

export default function ElderList() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [elders, setElders] = useState<ElderItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    apiGet<{ items: ElderItem[] }>('/api/configurator/elders')
      .then((data) => setElders(data.items))
      .catch((err) => setError(err instanceof Error ? err.message : '加载失败'))
      .finally(() => setLoading(false))
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  function formatDate(dt: string) {
    if (!dt) return '-'
    return new Date(dt).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-800">小伴 · 配置者端</h1>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-500 hover:text-gray-700 transition"
          >
            退出登录
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-700">服务中的老人</h2>
          <button
            onClick={() => navigate('/onboarding')}
            className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition"
          >
            为新老人开通服务
          </button>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 rounded-lg p-4 mb-4 text-sm">{error}</div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-400">加载中...</p>
          </div>
        ) : elders.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <div className="text-5xl mb-4">🌱</div>
            <p className="text-gray-500 text-lg mb-2">还没有老人在使用小伴</p>
            <p className="text-gray-400 text-sm">
              点击上方按钮，为第一位老人开通服务
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {elders.map((elder) => (
              <div
                key={elder.elder_id}
                onClick={() => navigate(`/confirmation/${elder.elder_id}`)}
                className="bg-white rounded-xl shadow-sm p-5 cursor-pointer hover:shadow-md hover:border-primary-200 border border-transparent transition"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center font-bold text-lg">
                      {(elder.nickname || '?')[0]}
                    </div>
                    <div>
                      <p className="font-medium text-gray-800">{elder.nickname || elder.elder_id.slice(0, 8)}</p>
                      <p className="text-xs text-gray-400 mt-0.5">创建于 {formatDate(elder.created_at)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {elder.profile_version && (
                      <span className="text-xs text-gray-400">v{elder.profile_version}</span>
                    )}
                    <span className={`text-xs px-2 py-1 rounded-full ${statusColors[elder.status] || 'bg-gray-100 text-gray-600'}`}>
                      {statusLabels[elder.status] || elder.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
