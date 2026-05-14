import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ConversationBrowser from './pages/ConversationBrowser'
import TagManagement from './pages/TagManagement'
import UnmetNeeds from './pages/UnmetNeeds'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="conversations" element={<ConversationBrowser />} />
          <Route path="tags" element={<TagManagement />} />
          <Route path="unmet-needs" element={<UnmetNeeds />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
