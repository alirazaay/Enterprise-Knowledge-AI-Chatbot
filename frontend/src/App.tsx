import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'
import KnowledgeBasePage from './pages/KnowledgeBasePage'

function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">Restoring session…</div>
  return isAuthenticated ? <DashboardPage /> : <Navigate to="/login" replace />
}

function AdminRoute() {
  const { isAuthenticated, isLoading, user } = useAuth()
  if (isLoading) return <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">Restoring session…</div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return user?.role === 'admin' ? <KnowledgeBasePage /> : <Navigate to="/dashboard" replace />
}

function App() {
  const { isAuthenticated } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/dashboard" element={<ProtectedRoute />} />
      <Route path="/knowledge-base" element={<AdminRoute />} />
      <Route path="*" element={<Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />} />
    </Routes>
  )
}

export default App
