import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { isAuthenticated } from './api/client'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ConversationBrowser from './pages/ConversationBrowser'
import TagManagement from './pages/TagManagement'
import UnmetNeeds from './pages/UnmetNeeds'
import TenantDetail from './pages/TenantDetail'

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="conversations" element={<ConversationBrowser />} />
          <Route path="tags" element={<TagManagement />} />
          <Route path="unmet-needs" element={<UnmetNeeds />} />
          <Route path="elders/:id" element={<TenantDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
