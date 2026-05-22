import { useState, useEffect, useCallback } from 'react'
import { apiGet, apiPatch } from '../api/client'

interface TagEntry {
  id: number
  tag: string
  confidence: number
  source: string
  message_content: string
  elder_nickname: string
  elder_id: number
  created_at: string
}

const TAG_OPTIONS = [
  '闲聊', '情感倾诉', '健康相关', '购物需求',
  '出行需求', '信息查询', '任务委托', '社交相关', '其他',
]

export default function TagManagement() {
  const [tags, setTags] = useState<TagEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState(false)
  const pageSize = 20

  const fetchTags = useCallback(() => {
    setLoading(true)
    setError('')
    apiGet<{ tags: TagEntry[]; total: number }>(`/api/admin/tags/review?page=${page}&page_size=${pageSize}`)
      .then((data) => { setTags(data.tags); setTotal(data.total) })
      .catch(() => setError('数据加载失败'))
      .finally(() => setLoading(false))
  }, [page])

  useEffect(() => { fetchTags() }, [fetchTags])

  async function handleSave(tagId: number) {
    setSaving(true)
    try {
      await apiPatch(`/api/admin/tags/${tagId}`, { new_tag: editValue })
      setTags((prev) => prev.map((t) => (t.id === tagId ? { ...t, tag: editValue } : t)))
      setEditingId(null)
    } catch {
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  function confidenceColor(c: number) {
    if (c < 0.4) return 'text-red-600 bg-red-50'
    if (c < 0.6) return 'text-yellow-600 bg-yellow-50'
    return 'text-green-600 bg-green-50'
  }

  const totalPages = Math.ceil(total / pageSize)

  if (loading) return <div className="text-gray-500 text-center py-20">加载中...</div>
  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 mb-4">{error}</p>
        <button onClick={fetchTags} className="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 text-sm">重试</button>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">标签审核</h2>

      {tags.length === 0 ? (
        <p className="text-gray-400 text-center py-10">暂无待审核标签</p>
      ) : (
        <>
          <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">用户</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">消息内容</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">当前标签</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">置信度</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">操作</th>
                </tr>
              </thead>
              <tbody>
                {tags.map((tag) => (
                  <tr key={tag.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{tag.elder_nickname}</td>
                    <td className="px-4 py-3 text-gray-600 max-w-[300px] truncate" title={tag.message_content}>
                      {tag.message_content.length > 50 ? tag.message_content.slice(0, 50) + '...' : tag.message_content}
                    </td>
                    <td className="px-4 py-3">
                      {editingId === tag.id ? (
                        <select
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                        >
                          {TAG_OPTIONS.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : (
                        <span className="inline-block px-2 py-0.5 bg-gray-100 rounded text-xs">{tag.tag}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${confidenceColor(tag.confidence)}`}>
                        {(tag.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {editingId === tag.id ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSave(tag.id)}
                            disabled={saving}
                            className="px-3 py-1 bg-primary-600 text-white rounded text-xs hover:bg-primary-700 disabled:opacity-50"
                          >
                            {saving ? '保存中...' : '保存'}
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300"
                          >
                            取消
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => { setEditingId(tag.id); setEditValue(tag.tag) }}
                          className="px-3 py-1 border border-gray-300 rounded text-xs hover:bg-gray-50"
                        >
                          编辑
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-gray-500">共 {total} 条，第 {page}/{totalPages} 页</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 border rounded text-sm disabled:opacity-50 hover:bg-gray-50"
                >
                  上一页
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 border rounded text-sm disabled:opacity-50 hover:bg-gray-50"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
