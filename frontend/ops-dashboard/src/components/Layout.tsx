import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { clearCredentials } from '../api/client'

const navigation = [
  { name: '仪表盘', href: '/dashboard' },
  { name: '对话浏览', href: '/conversations' },
  { name: '标签审核', href: '/tags' },
  { name: '未满足需求', href: '/unmet-needs' },
]

export default function Layout() {
  const navigate = useNavigate()

  function handleLogout() {
    clearCredentials()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col">
        <h1 className="text-xl font-bold text-primary-700 mb-8">小伴运营后台</h1>
        <nav className="space-y-1 flex-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-50'
                }`
              }
            >
              {item.name}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          className="mt-4 px-3 py-2 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md text-left"
        >
          退出登录
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto p-6 bg-gray-50">
        <Outlet />
      </main>
    </div>
  )
}
