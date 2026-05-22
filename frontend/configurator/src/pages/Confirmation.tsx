import { useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { apiPost } from '../api/client'

interface LocationState {
  summary?: string
}

export default function Confirmation() {
  const { elderId } = useParams<{ elderId: string }>()
  const location = useLocation()
  const state = location.state as LocationState | null
  const navigate = useNavigate()

  const [showAddMore, setShowAddMore] = useState(false)
  const [additionalText, setAdditionalText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [updatedSummary, setUpdatedSummary] = useState('')

  const summary = updatedSummary || state?.summary || ''

  const handleAddMore = async () => {
    if (!additionalText.trim()) return
    setError('')
    setLoading(true)
    try {
      const data = await apiPost<{ summary: string }>(
        `/api/configurator/elders/${elderId}/profile`,
        {
          profile_text: additionalText.trim(),
          contributor_relationship: '',
        }
      )
      setUpdatedSummary(data.summary)
      setAdditionalText('')
      setShowAddMore(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <button
            onClick={() => navigate('/')}
            className="text-sm text-gray-500 hover:text-gray-700 transition"
          >
            ← 返回首页
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm p-8">
          <div className="text-center mb-6">
            <div className="text-4xl mb-3">✅</div>
            <h1 className="text-2xl font-bold text-gray-800">小伴已了解</h1>
          </div>

          {/* Summary display */}
          {summary && (
            <div className="bg-primary-50 rounded-lg p-5 mb-8">
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {summary}
              </p>
            </div>
          )}

          {/* Action buttons */}
          {!showAddMore ? (
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => navigate('/')}
                className="flex-1 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition"
              >
                看起来不错
              </button>
              <button
                onClick={() => setShowAddMore(true)}
                className="flex-1 py-3 border-2 border-primary-600 text-primary-700 font-medium rounded-lg hover:bg-primary-50 transition"
              >
                我想补充更多
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <label className="block text-sm font-medium text-gray-700">
                补充更多信息
              </label>
              <textarea
                value={additionalText}
                onChange={(e) => setAdditionalText(e.target.value)}
                placeholder="还有什么想告诉小伴的..."
                rows={5}
                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition resize-y"
                style={{ minHeight: '120px' }}
              />

              {error && (
                <p className="text-red-500 text-sm">{error}</p>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handleAddMore}
                  disabled={loading || !additionalText.trim()}
                  className="flex-1 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? '提交中...' : '提交补充'}
                </button>
                <button
                  onClick={() => setShowAddMore(false)}
                  className="px-6 py-3 text-gray-500 hover:text-gray-700 font-medium rounded-lg transition"
                >
                  取消
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
