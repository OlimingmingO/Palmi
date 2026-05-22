import { useState, useEffect } from 'react'
import { apiGet } from '../api/client'

interface DashboardStats {
  total_users: number
  dau: number
  wau: number
  total_messages: number
  active_count: number
  silent_count: number
  at_risk_count: number
  new_count: number
  avg_session_depth: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  function fetchData() {
    setLoading(true)
    setError('')
    apiGet<DashboardStats>('/api/admin/stats/dashboard')
      .then(setStats)
      .catch(() => setError('数据加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  if (loading) {
    return <div className="text-gray-500 text-center py-20">加载中...</div>
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 mb-4">{error}</p>
        <button onClick={fetchData} className="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 text-sm">
          重试
        </button>
      </div>
    )
  }

  if (!stats) return null

  const metricCards = [
    { label: '总用户数', value: stats.total_users, color: 'border-primary-500' },
    { label: '日活跃 (DAU)', value: stats.dau, color: 'border-green-500' },
    { label: '周活跃 (WAU)', value: stats.wau, color: 'border-blue-500' },
    { label: '总消息数', value: stats.total_messages, color: 'border-purple-500' },
    { label: '平均会话深度', value: stats.avg_session_depth.toFixed(1), color: 'border-indigo-500' },
  ]

  const statusCards = [
    { label: '活跃', value: stats.active_count, bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-500' },
    { label: '沉默', value: stats.silent_count, bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-500' },
    { label: '流失风险', value: stats.at_risk_count, bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-500' },
    { label: '新用户', value: stats.new_count, bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-500' },
  ]

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">仪表盘</h2>

      {/* Metric cards */}
      <div className="grid grid-cols-5 gap-4 mb-8">
        {metricCards.map((card) => (
          <div key={card.label} className={`bg-white rounded-lg shadow-sm border-l-4 ${card.color} p-4`}>
            <p className="text-sm text-gray-500">{card.label}</p>
            <p className="text-3xl font-bold mt-1">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Status breakdown */}
      <h3 className="text-lg font-semibold mb-4">用户状态分布</h3>
      <div className="grid grid-cols-4 gap-4">
        {statusCards.map((card) => (
          <div key={card.label} className={`rounded-lg shadow-sm border-l-4 ${card.border} ${card.bg} p-5`}>
            <p className={`text-sm font-medium ${card.text}`}>{card.label}</p>
            <p className={`text-4xl font-bold mt-2 ${card.text}`}>{card.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
