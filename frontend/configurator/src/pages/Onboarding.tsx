import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiPost } from '../api/client'

const RELATIONSHIPS = ['子女', '社工', '邻居', '老伴', '本人'] as const

interface CreateElderResponse {
  elder_id: string
  summary: string
  understanding_doc_version: number
}

export default function Onboarding() {
  const [nickname, setNickname] = useState('')
  const [relationship, setRelationship] = useState<string>(RELATIONSHIPS[0])
  const [profileText, setProfileText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!nickname.trim() || !profileText.trim()) {
      setError('请填写老人昵称和介绍信息')
      return
    }
    setError('')
    setLoading(true)
    try {
      const data = await apiPost<CreateElderResponse>('/api/configurator/elders', {
        nickname: nickname.trim(),
        profile_text: profileText.trim(),
        contributor_relationship: relationship,
        contributor_name: '',
      })
      navigate(`/confirmation/${data.elder_id}`, {
        state: { summary: data.summary },
      })
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
            ← 返回
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">
          向小伴介绍一位老人
        </h1>
        <p className="text-gray-500 mb-8 leading-relaxed">
          用你自己的话，跟小伴介绍一下这位老人。什么信息都行——兴趣、性格、家庭、健康、日常习惯、忌讳……你觉得什么能帮小伴更好地陪伴他/她，就写什么。
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Nickname */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              老人昵称
            </label>
            <input
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="例如：美兰阿姨"
              className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
            />
          </div>

          {/* Relationship */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              你与老人的关系
            </label>
            <select
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition bg-white"
            >
              {RELATIONSHIPS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          {/* Profile text */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              介绍信息
            </label>
            <textarea
              value={profileText}
              onChange={(e) => setProfileText(e.target.value)}
              placeholder="我妈叫张美兰，68岁，我们都叫她美兰阿姨。住在普陀区，退休前是小学语文老师。她性格开朗，喜欢跳广场舞，每天早上六点就去公园打太极。最近记性不太好，经常忘记吃药。她最爱看戏曲频道，尤其是越剧。家里还养了一只叫'团团'的橘猫..."
              rows={8}
              className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition resize-y"
              style={{ minHeight: '200px' }}
            />
          </div>

          {error && (
            <p className="text-red-500 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                小伴正在理解中...
              </span>
            ) : '提交给小伴'}
          </button>
        </form>
      </main>
    </div>
  )
}
