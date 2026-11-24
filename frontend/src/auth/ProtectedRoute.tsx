import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from './AuthContext'
import { LoadingScreen } from '../components/ui/LoadingScreen'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <LoadingScreen label="Checking session…" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}