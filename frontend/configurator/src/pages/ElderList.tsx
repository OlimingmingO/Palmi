import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ElderList() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
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

        {/* Empty state */}
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <div className="text-5xl mb-4">🌱</div>
          <p className="text-gray-500 text-lg mb-2">还没有老人在使用小伴</p>
          <p className="text-gray-400 text-sm">
            点击上方按钮，为第一位老人开通服务
          </p>
        </div>
      </main>
    </div>
  )
}
