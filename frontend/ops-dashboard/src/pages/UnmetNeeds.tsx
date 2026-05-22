import { useState, useEffect } from 'react'
import { apiGet, apiPatch } from '../api/client'

interface Category {
  need_category: string
  total_occurrences: number
  elder_count: number
  elder_nicknames: string[]
}

interface NeedItem {
  id: number
  need_description: string
  need_category: string
  confidence: number
  occurrence_count: number
  elder_id: number
  created_at: string
}

export default function UnmetNeeds() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedCat, setExpandedCat] = useState<string | null>(null)
  const [needs, setNeeds] = useState<NeedItem[]>([])
  const [needsLoading, setNeedsLoading] = useState(false)
  const [dismissing, setDismissing] = useState<number | null>(null)

  function fetchCategories() {
    setLoading(true)
    setError('')
    apiGet<{ items: Category[] }>('/api/admin/unmet-needs')
      .then((data) => setCategories(data.items))
      .catch(() => setError('数据加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchCategories() }, [])

  function toggleCategory(cat: string) {
    if (expandedCat === cat) {
      setExpandedCat(null)
      setNeeds([])
      return
    }
    setExpandedCat(cat)
    setNeedsLoading(true)
    apiGet<{ items: NeedItem[] }>(`/api/admin/unmet-needs?category=${encodeURIComponent(cat)}`)
      .then((data) => setNeeds(data.items))
      .catch(() => setNeeds([]))
      .finally(() => setNeedsLoading(false))
  }

  async function handleDismiss(id: number) {
    setDismissing(id)
    try {
      await apiPatch(`/api/admin/unmet-needs/${id}/dismiss`)
      setNeeds((prev) => prev.filter((n) => n.id !== id))
      // Update count in categories
      if (expandedCat) {
        setCategories((prev) =>
          prev.map((c) =>
            c.need_category === expandedCat
              ? { ...c, total_occurrences: c.total_occurrences - 1 }
              : c
          ).filter((c) => c.total_occurrences > 0)
        )
      }
    } catch {
      alert('操作失败')
    } finally {
      setDismissing(null)
    }
  }

  if (loading) return <div className="text-gray-500 text-center py-20">加载中...</div>
  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 mb-4">{error}</p>
        <button onClick={fetchCategories} className="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 text-sm">重试</button>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">未满足需求</h2>

      {categories.length === 0 ? (
        <p className="text-gray-400 text-center py-10">暂无未满足需求</p>
      ) : (
        <div className="space-y-4">
          {categories.map((cat) => (
            <div key={cat.need_category} className="bg-white rounded-lg shadow-sm border overflow-hidden">
              {/* Category header */}
              <div
                onClick={() => toggleCategory(cat.need_category)}
                className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-gray-50"
              >
                <div>
                  <h3 className="font-semibold text-base">{cat.need_category}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    涉及用户: {cat.elder_nicknames.join('、') || '-'}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="bg-red-50 text-red-700 text-sm font-medium px-3 py-1 rounded-full">
                    {cat.total_occurrences} 次
                  </span>
                  <span className="text-gray-400 text-sm">
                    {expandedCat === cat.need_category ? '▲' : '▼'}
                  </span>
                </div>
              </div>

              {/* Expanded needs list */}
              {expandedCat === cat.need_category && (
                <div className="border-t px-5 py-3">
                  {needsLoading ? (
                    <p className="text-gray-400 text-center py-4 text-sm">加载中...</p>
                  ) : needs.length === 0 ? (
                    <p className="text-gray-400 text-center py-4 text-sm">暂无数据</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-500 border-b">
                          <th className="text-left py-2 font-medium">需求描述</th>
                          <th className="text-left py-2 font-medium w-24">置信度</th>
                          <th className="text-left py-2 font-medium w-28">出现次数</th>
                          <th className="text-left py-2 font-medium w-32">创建时间</th>
                          <th className="text-right py-2 font-medium w-20">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {needs.map((need) => (
                          <tr key={need.id} className="border-b last:border-0 hover:bg-gray-50">
                            <td className="py-2 text-gray-700">{need.need_description}</td>
                            <td className="py-2">
                              <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                                need.confidence < 0.4 ? 'bg-red-50 text-red-600' :
                                need.confidence < 0.6 ? 'bg-yellow-50 text-yellow-600' :
                                'bg-green-50 text-green-600'
                              }`}>
                                {(need.confidence * 100).toFixed(0)}%
                              </span>
                            </td>
                            <td className="py-2 text-gray-500">{need.occurrence_count}</td>
                            <td className="py-2 text-gray-400">
                              {new Date(need.created_at).toLocaleDateString('zh-CN')}
                            </td>
                            <td className="py-2 text-right">
                              <button
                                onClick={() => handleDismiss(need.id)}
                                disabled={dismissing === need.id}
                                className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                              >
                                {dismissing === need.id ? '处理中...' : '忽略'}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
