import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { apiGet, apiPatch } from '../api/client'

interface ConfiguratorInfo {
  id: string
  nickname: string
  relationship: string
  phone: string | null
  is_primary: boolean
  created_at: string
}

interface ElderDetail {
  id: string
  nickname: string
  wechat_user_id: string
  phone: string | null
  status: string
  engagement_status: string
  created_at: string
  conversation_stats: {
    total_messages: number
    total_sessions: number
    weekly_messages: number
    avg_daily_messages: number
    recent_messages: { id: string; role: string; preview: string; created_at: string }[]
  }
  tag_distribution: Record<string, number>
  trigger_history: {
    id: string
    trigger_type: string
    status: string
    reason: string
    skip_reason: string | null
    created_at: string
  }[]
  pke_status: {
    raw_file_count: number
    wiki_file_count: number
    raw_last_modified: string | null
    wiki_last_modified: string | null
  }
  config_status: {
    has_profile: boolean
    version: number | null
    last_updated_by: string | null
    updated_at: string | null
    content: string | null
  } | null
  configurators: ConfiguratorInfo[]
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
  const [bindId, setBindId] = useState('')
  const [binding, setBinding] = useState(false)
  const [bindError, setBindError] = useState('')
  const [bindSuccess, setBindSuccess] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    apiGet<ElderDetail>(`/api/admin/elders/${id}`)
      .then(setData)
      .catch(() => setError('数据加载失败'))
      .finally(() => setLoading(false))
  }, [id])

  async function handleBind() {
    setBinding(true)
    setBindError('')
    setBindSuccess('')
    try {
      await apiPatch(`/api/admin/elders/${id}/bind`, { wechat_user_id: bindId.trim() })
      setBindSuccess('绑定成功！页面即将刷新...')
      setTimeout(() => window.location.reload(), 1500)
    } catch (err) {
      setBindError(err instanceof Error ? err.message : '绑定失败')
    } finally {
      setBinding(false)
    }
  }

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

  const { conversation_stats, tag_distribution, trigger_history, pke_status, config_status, configurators } = data

  const pieData = Object.entries(tag_distribution)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700 text-sm">&larr; 返回</button>
        <h2 className="text-2xl font-bold">{data.nickname}</h2>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusBadge[data.status] || 'bg-gray-100 text-gray-700'}`}>
          {data.status}
        </span>
        <button
          onClick={() => navigate('/conversations')}
          className="ml-auto text-sm text-primary-600 hover:underline"
        >
          查看完整对话
        </button>
      </div>

      {/* Binding status */}
      {data.wechat_user_id.startsWith('web_') ? (
        <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs font-medium rounded">
              未绑定企微
            </span>
            <span className="text-sm text-gray-500">该老人由配置者端创建，尚未关联企业微信账号</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={bindId}
              onChange={(e) => setBindId(e.target.value)}
              placeholder="输入企微用户ID (external_userid)"
              className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm"
            />
            <button
              onClick={handleBind}
              disabled={binding || !bindId.trim()}
              className="px-4 py-1.5 bg-primary-600 text-white text-sm rounded hover:bg-primary-700 disabled:opacity-50"
            >
              {binding ? '绑定中...' : '绑定'}
            </button>
          </div>
          {bindError && <p className="text-red-500 text-xs mt-2">{bindError}</p>}
          {bindSuccess && <p className="text-green-600 text-xs mt-2">{bindSuccess}</p>}
        </div>
      ) : (
        <div className="mb-4 flex items-center gap-2">
          <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs font-medium rounded">
            已绑定企微
          </span>
          <span className="text-sm text-gray-400">{data.wechat_user_id}</span>
        </div>
      )}

      {/* 6-zone grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* 1. Basic Info — Identity */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">用户身份信息</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">昵称</dt><dd className="font-medium">{data.nickname}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">系统ID</dt><dd className="text-xs text-gray-400 truncate max-w-[180px]">{data.id}</dd></div>
            <div className="flex justify-between">
              <dt className="text-gray-500">企微用户ID</dt>
              <dd className="truncate max-w-[180px] text-xs font-mono">{data.wechat_user_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">绑定状态</dt>
              <dd>
                {data.wechat_user_id.startsWith('web_') ? (
                  <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded">未绑定</span>
                ) : (
                  <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded">已绑定</span>
                )}
              </dd>
            </div>
            <div className="flex justify-between"><dt className="text-gray-500">活跃状态</dt><dd>{data.engagement_status}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">创建时间</dt><dd>{formatDate(data.created_at)}</dd></div>
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
                    <span className="truncate">{msg.preview}</span>
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
                          t.status === 'sent' ? 'bg-green-50 text-green-600' :
                          t.status === 'failed' ? 'bg-red-50 text-red-600' :
                          t.status === 'skipped' ? 'bg-yellow-50 text-yellow-600' :
                          'bg-gray-100 text-gray-600'
                        }`}>{t.status}</span>
                      </td>
                      <td className="py-1.5 text-gray-500 max-w-[150px] truncate" title={t.reason}>{t.reason}</td>
                      <td className="py-1.5 text-gray-400">{formatDate(t.created_at)}</td>
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
            <div className="flex justify-between"><dt className="text-gray-500">原始文件数</dt><dd className="font-medium">{pke_status.raw_file_count}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Wiki 文件数</dt><dd className="font-medium">{pke_status.wiki_file_count}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">最后采集时间</dt><dd>{formatDate(pke_status.raw_last_modified)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">最后编译时间</dt><dd>{formatDate(pke_status.wiki_last_modified)}</dd></div>
          </dl>
        </div>

        {/* 6. Configuration Info */}
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">配置信息</h3>

          {/* Configurator(s) list */}
          {configurators && configurators.length > 0 ? (
            <div className="mb-4">
              <p className="text-xs font-medium text-gray-500 mb-2">配置者</p>
              <div className="space-y-2">
                {configurators.map((c) => (
                  <div key={c.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded text-sm">
                    <span className="font-medium">{c.nickname || '未命名'}</span>
                    <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 text-xs rounded">{c.relationship}</span>
                    {c.is_primary && <span className="px-1.5 py-0.5 bg-orange-50 text-orange-600 text-xs rounded">主要联系人</span>}
                    {c.phone && <span className="text-gray-400 text-xs">{c.phone}</span>}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-gray-400 text-sm mb-4">暂无配置者信息</p>
          )}

          {/* Profile version info */}
          {config_status && config_status.has_profile ? (
            <div>
              <div className="flex items-center gap-3 mb-2 text-xs text-gray-500">
                <span>版本 v{config_status.version}</span>
                <span>·</span>
                <span>由 {config_status.last_updated_by} 更新</span>
                <span>·</span>
                <span>{formatDate(config_status.updated_at)}</span>
              </div>
              {/* Profile content */}
              {config_status.content && (
                <div className="mt-2 p-3 bg-gray-50 rounded border text-xs text-gray-700 max-h-[200px] overflow-auto whitespace-pre-wrap">
                  {config_status.content}
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">暂无档案配置</p>
          )}

          {/* Linkage indicator */}
          {configurators && configurators.length > 0 && (
            <div className="mt-3 pt-3 border-t text-xs text-gray-500">
              <span>关联关系：</span>
              <span className="font-medium text-gray-700">{data.nickname}</span>
              <span className="mx-1">←</span>
              <span>由 </span>
              <span className="font-medium text-blue-600">{configurators[0].nickname || '配置者'}</span>
              <span>（{configurators[0].relationship}）配置</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
