import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Spinner } from '../components/ui'
import { useAuth } from './AuthContext'
import type { Role } from '../lib/types'

interface ProtectedRouteProps {
  roles?: Role[]
}

export function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const { loading, isAuthenticated, principal } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div style={{ padding: '4rem', display: 'grid', placeItems: 'center' }}>
        <Spinner label="Checking session…" />
      </div>
    )
  }

  if (!isAuthenticated || !principal) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (roles && !roles.includes(principal.role)) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
