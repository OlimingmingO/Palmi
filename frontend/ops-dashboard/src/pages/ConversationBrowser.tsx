import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiGet } from '../api/client'

interface Elder {
  id: number
  nickname: string
  engagement_status: string
  last_message_at: string | null
  total_messages: number
}

interface DateEntry {
  date: string
  message_count: number
  preview: string
}

interface Message {
  id: number
  role: string
  content: string
  created_at: string
}

interface SearchResult {
  id: number
  content: string
  elder_nickname: string
  elder_id: number
  created_at: string
}

const statusColors: Record<string, string> = {
  active: 'bg-green-500',
  silent: 'bg-yellow-500',
  at_risk: 'bg-red-500',
  new: 'bg-blue-500',
}

const statusLabels: Record<string, string> = {
  active: '活跃',
  silent: '沉默',
  at_risk: '流失风险',
  new: '新用户',
}

export default function ConversationBrowser() {
  const navigate = useNavigate()
  const [elders, setElders] = useState<Elder[]>([])
  const [selectedElder, setSelectedElder] = useState<Elder | null>(null)
  const [dates, setDates] = useState<DateEntry[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState({ elders: true, dates: false, messages: false })
  const [error, setError] = useState('')

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    apiGet<Elder[]>('/api/admin/elders')
      .then(setElders)
      .catch(() => setError('加载用户列表失败'))
      .finally(() => setLoading((p) => ({ ...p, elders: false })))
  }, [])

  const selectElder = useCallback((elder: Elder) => {
    setSelectedElder(elder)
    setSelectedDate('')
    setMessages([])
    setSearchResults(null)
    setLoading((p) => ({ ...p, dates: true }))
    apiGet<{ dates: DateEntry[] }>(`/api/admin/elders/${elder.id}/conversations`)
      .then((data) => setDates(data.dates))
      .catch(() => setDates([]))
      .finally(() => setLoading((p) => ({ ...p, dates: false })))
  }, [])

  const selectDate = useCallback((date: string) => {
    if (!selectedElder) return
    setSelectedDate(date)
    setLoading((p) => ({ ...p, messages: true }))
    apiGet<{ messages: Message[] }>(`/api/admin/elders/${selectedElder.id}/conversations?date=${date}`)
      .then((data) => setMessages(data.messages))
      .catch(() => setMessages([]))
      .finally(() => setLoading((p) => ({ ...p, messages: false })))
  }, [selectedElder])

  function handleSearch() {
    if (!searchQuery.trim()) { setSearchResults(null); return }
    setSearching(true)
    apiGet<{ results: SearchResult[] }>(`/api/admin/conversations/search?q=${encodeURIComponent(searchQuery)}`)
      .then((data) => setSearchResults(data.results))
      .catch(() => setSearchResults([]))
      .finally(() => setSearching(false))
  }

  function formatTime(dt: string | null) {
    if (!dt) return '-'
    return new Date(dt).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  }

  if (loading.elders) {
    return <div className="text-gray-500 text-center py-20">加载中...</div>
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search bar */}
      <div className="flex items-center gap-2 mb-4">
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="搜索对话内容..."
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm hover:bg-primary-700 disabled:opacity-50"
        >
          {searching ? '搜索中...' : '搜索'}
        </button>
        {searchResults !== null && (
          <button onClick={() => setSearchResults(null)} className="text-sm text-gray-500 hover:text-gray-700">
            清除
          </button>
        )}
      </div>

      {error && <p className="text-red-500 text-sm mb-2">{error}</p>}

      {/* Search results overlay */}
      {searchResults !== null ? (
        <div className="bg-white rounded-lg shadow-sm border p-4 overflow-auto flex-1">
          <h3 className="font-semibold mb-3">搜索结果 ({searchResults.length})</h3>
          {searchResults.length === 0 ? (
            <p className="text-gray-400">暂无匹配结果</p>
          ) : (
            <div className="space-y-2">
              {searchResults.map((r) => (
                <div
                  key={r.id}
                  className="p-3 border rounded hover:bg-gray-50 cursor-pointer"
                  onClick={() => {
                    const elder = elders.find((e) => e.id === r.elder_id)
                    if (elder) { selectElder(elder); setSearchResults(null) }
                  }}
                >
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{r.elder_nickname}</span>
                    <span className="text-gray-400">{formatTime(r.created_at)}</span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">{r.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Three-panel layout */
        <div className="flex flex-1 min-h-0 gap-4">
          {/* Left: Elder list */}
          <div className="w-[250px] flex-shrink-0 bg-white rounded-lg shadow-sm border overflow-auto">
            <div className="p-3 border-b bg-gray-50">
              <h3 className="text-sm font-semibold text-gray-700">用户列表 ({elders.length})</h3>
            </div>
            {elders.map((elder) => (
              <div
                key={elder.id}
                onClick={() => selectElder(elder)}
                className={`px-3 py-3 border-b cursor-pointer hover:bg-gray-50 ${
                  selectedElder?.id === elder.id ? 'bg-primary-50 border-l-2 border-l-primary-500' : ''
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${statusColors[elder.engagement_status] || 'bg-gray-400'}`} />
                  <span className="text-sm font-medium truncate">{elder.nickname}</span>
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-xs text-gray-400">{statusLabels[elder.engagement_status] || elder.engagement_status}</span>
                  <span className="text-xs text-gray-400">{formatTime(elder.last_message_at)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Middle: Date timeline */}
          <div className="w-[300px] flex-shrink-0 bg-white rounded-lg shadow-sm border overflow-auto">
            <div className="p-3 border-b bg-gray-50 flex justify-between items-center">
              <h3 className="text-sm font-semibold text-gray-700">
                {selectedElder ? `${selectedElder.nickname} 的对话` : '请选择用户'}
              </h3>
              {selectedElder && (
                <button
                  onClick={() => navigate(`/elders/${selectedElder.id}`)}
                  className="text-xs text-primary-600 hover:underline"
                >
                  详情
                </button>
              )}
            </div>
            {loading.dates ? (
              <p className="text-gray-400 text-center py-8 text-sm">加载中...</p>
            ) : !selectedElder ? (
              <p className="text-gray-400 text-center py-8 text-sm">← 选择一个用户</p>
            ) : dates.length === 0 ? (
              <p className="text-gray-400 text-center py-8 text-sm">暂无对话记录</p>
            ) : (
              dates.map((d) => (
                <div
                  key={d.date}
                  onClick={() => selectDate(d.date)}
                  className={`px-3 py-3 border-b cursor-pointer hover:bg-gray-50 ${
                    selectedDate === d.date ? 'bg-primary-50' : ''
                  }`}
                >
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">{d.date}</span>
                    <span className="text-xs text-gray-400">{d.message_count} 条</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 truncate">{d.preview}</p>
                </div>
              ))
            )}
          </div>

          {/* Right: Conversation messages */}
          <div className="flex-1 bg-white rounded-lg shadow-sm border flex flex-col overflow-hidden">
            <div className="p-3 border-b bg-gray-50">
              <h3 className="text-sm font-semibold text-gray-700">
                {selectedDate ? `${selectedDate} 对话详情` : '请选择日期'}
              </h3>
            </div>
            <div className="flex-1 overflow-auto p-4 space-y-3">
              {loading.messages ? (
                <p className="text-gray-400 text-center py-8 text-sm">加载中...</p>
              ) : !selectedDate ? (
                <p className="text-gray-400 text-center py-8 text-sm">← 选择一个日期查看对话</p>
              ) : messages.length === 0 ? (
                <p className="text-gray-400 text-center py-8 text-sm">暂无消息</p>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[70%] rounded-lg px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-primary-500 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      <p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-primary-100' : 'text-gray-400'}`}>
                        {new Date(msg.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
