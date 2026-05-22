import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { apiGet } from '../api/client'

interface ElderDetail {
  elder: {
    id: number
    wechat_user_id: string
    nickname: string
    status: string
    created_at: string
  }
  conversation_stats: {
    total_messages: number
    total_sessions: number
    weekly_messages: number
    avg_daily_messages: number
    recent_messages: { content: string; role: string; created_at: string }[]
  }
  tag_distribution: Record<string, number>
  trigger_history: {
    id: number
    trigger_type: string
    status: string
    trigger_reason: string
    triggered_at: string
  }[]
  pke_status: {
    raw_count: number
    wiki_count: number
    last_raw_modified: string | null
    last_wiki_modified: string | null
  }
  config_status: {
    has_profile: boolean
    version: number | null
    last_updated_by: string | null
    updated_at: string | null
  }
}

const PIE_COLORS = ['#0ea5e9', '#22c55e', '#eab308', '#ef4444', '#8b5cf6', '#f97316', '#ec4899', '#14b8a6', '#6366f1']

const statusBadge: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  silent: 'bg-yellow-100 text-yellow-700',
  at_risk: 'bg-red-100 text-red-700',
  new: 'bg-blue-100 text-blue-700',
}

export default function TenantDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<ElderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    apiGet<ElderDetail>(`/api/admin/elders/${id}`)
      .then(setData)
      .catch(() => setError('数据加载失败'))
      .finally(() => setLoading(false))
  }, [id])

  function formatDate(dt: string | null) {
    if (!dt) return '-'
    return new Date(dt).toLocaleString('zh-CN')
  }

  if (loading) return <div className="text-gray-500 text-center py-20">加载中...</div>
  if (error || !data) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 mb-4">{error || '数据加载失败'}</p>
        <button onClick={() => navigate(-1)} className="px-4 py-2 bg-gray-200 rounded text-sm hover:bg-gray-300">返回</button>
      </div>
    )
  }

  const { elder, conversation_stats, tag_distribution, trigger_history, pke_status, config_status } = data

  const pieData = Object.entries(tag_distribution)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700 text-sm">&larr; 返回</button>
        <h2 className="text-2xl font-bold">{elder.nickname}</h2>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusBadge[elder.status] || 'bg-gray-100 text-gray-700'}`}>
          {elder.status}
        </span>
        <button
          onClick={() => navigate('/conversations')}
          className="ml-auto text-sm text-primary-600 hover:underline"
        >
          查看完整对话
        </button>
      </div>

      {/* 6-zone grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* 1. Basic Info */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">基本信息</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">ID</dt><dd>{elder.id}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">微信ID</dt><dd className="truncate max-w-[200px]">{elder.wechat_user_id}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">状态</dt><dd>{elder.status}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">创建时间</dt><dd>{formatDate(elder.created_at)}</dd></div>
          </dl>
        </div>

        {/* 2. Conversation Stats */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">对话统计</h3>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-gray-50 rounded p-2 text-center">
              <p className="text-2xl font-bold">{conversation_stats.total_messages}</p>
              <p className="text-xs text-gray-500">总消息数</p>
            </div>
            <div className="bg-gray-50 rounded p-2 text-center">
              <p className="text-2xl font-bold">{conversation_stats.total_sessions}</p>
              <p className="text-xs text-gray-500">总会话数</p>
            </div>
            <div className="bg-gray-50 rounded p-2 text-center">
              <p className="text-2xl font-bold">{conversation_stats.weekly_messages}</p>
              <p className="text-xs text-gray-500">本周消息</p>
            </div>
            <div className="bg-gray-50 rounded p-2 text-center">
              <p className="text-2xl font-bold">{conversation_stats.avg_daily_messages.toFixed(1)}</p>
              <p className="text-xs text-gray-500">日均消息</p>
            </div>
          </div>
          {conversation_stats.recent_messages.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">最近消息</p>
              <div className="space-y-1 max-h-32 overflow-auto">
                {conversation_stats.recent_messages.slice(0, 5).map((msg, i) => (
                  <div key={i} className="text-xs text-gray-600 flex gap-2">
                    <span className={`font-medium ${msg.role === 'user' ? 'text-primary-600' : 'text-gray-400'}`}>
                      {msg.role === 'user' ? '用户' : '小伴'}
                    </span>
                    <span className="truncate">{msg.content}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 3. Tag Distribution */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">意图标签分布</h3>
          {pieData.length === 0 ? (
            <p className="text-gray-400 text-center py-8 text-sm">暂无标签数据</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={11}>
                  {pieData.map((_entry, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* 4. Trigger History */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">触发历史</h3>
          {trigger_history.length === 0 ? (
            <p className="text-gray-400 text-center py-8 text-sm">暂无触发记录</p>
          ) : (
            <div className="max-h-[260px] overflow-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-white">
                  <tr className="text-gray-500 border-b">
                    <th className="text-left py-1.5 font-medium">类型</th>
                    <th className="text-left py-1.5 font-medium">状态</th>
                    <th className="text-left py-1.5 font-medium">原因</th>
                    <th className="text-left py-1.5 font-medium">时间</th>
                  </tr>
                </thead>
                <tbody>
                  {trigger_history.slice(0, 20).map((t) => (
                    <tr key={t.id} className="border-b last:border-0">
                      <td className="py-1.5">{t.trigger_type}</td>
                      <td className="py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-xs ${
                          t.status === 'completed' ? 'bg-green-50 text-green-600' :
                          t.status === 'failed' ? 'bg-red-50 text-red-600' :
                          'bg-gray-100 text-gray-600'
                        }`}>{t.status}</span>
                      </td>
                      <td className="py-1.5 text-gray-500 max-w-[150px] truncate" title={t.trigger_reason}>{t.trigger_reason}</td>
                      <td className="py-1.5 text-gray-400">{formatDate(t.triggered_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 5. PKE Status */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">PKE 状态</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">原始文件数</dt><dd className="font-medium">{pke_status.raw_count}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Wiki 文件数</dt><dd className="font-medium">{pke_status.wiki_count}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">最后采集时间</dt><dd>{formatDate(pke_status.last_raw_modified)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">最后编译时间</dt><dd>{formatDate(pke_status.last_wiki_modified)}</dd></div>
          </dl>
        </div>

        {/* 6. Config Status */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">配置状态</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">已配置档案</dt>
              <dd>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${config_status.has_profile ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-500'}`}>
                  {config_status.has_profile ? '是' : '否'}
                </span>
              </dd>
            </div>
            <div className="flex justify-between"><dt className="text-gray-500">版本</dt><dd>{config_status.version ?? '-'}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">最后更新者</dt><dd>{config_status.last_updated_by ?? '-'}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">更新时间</dt><dd>{formatDate(config_status.updated_at)}</dd></div>
          </dl>
        </div>
      </div>
    </div>
  )
}
