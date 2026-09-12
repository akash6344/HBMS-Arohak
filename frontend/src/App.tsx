import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppShell } from './components/layout/AppShell/AppShell'
import { Spinner } from './components/ui'
import { CustomerBookingsPage } from './pages/CustomerBookingsPage'
import { CustomerSearchPage } from './pages/CustomerSearchPage'
import { HotelInfoChatPage } from './pages/HotelInfoChatPage'
import { LoginPage } from './pages/LoginPage'
import { PlatformOrganizationsPage } from './pages/PlatformOrganizationsPage'
import { RegisterPage } from './pages/RegisterPage'
import { StaffBookingsPage } from './pages/StaffBookingsPage'
import { StaffCancellationsPage } from './pages/StaffCancellationsPage'
import { StaffRoomsPage } from './pages/StaffRoomsPage'
import { StaffTeamPage } from './pages/StaffTeamPage'
import type { Role } from './lib/types'

function HomeRedirect() {
  const { loading, principal } = useAuth()
  if (loading) {
    return (
      <div style={{ padding: '4rem', display: 'grid', placeItems: 'center' }}>
        <Spinner />
      </div>
    )
  }
  if (!principal) return <Navigate to="/login" replace />
  const roleHomes: Record<Role, string> = {
    CUSTOMER: '/search',
    PRODUCT_ADMIN: '/platform/organizations',
    ORG_ADMIN: '/staff/bookings',
    RECEPTIONIST: '/staff/bookings',
  }
  return <Navigate to={roleHomes[principal.role]} replace />
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<HomeRedirect />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route element={<ProtectedRoute roles={['CUSTOMER']} />}>
              <Route path="/search" element={<CustomerSearchPage />} />
              <Route path="/my-bookings" element={<CustomerBookingsPage />} />
            </Route>

            <Route
              element={
                <ProtectedRoute
                  roles={['CUSTOMER', 'PRODUCT_ADMIN', 'ORG_ADMIN', 'RECEPTIONIST']}
                />
              }
            >
              <Route path="/hotel-info" element={<HotelInfoChatPage />} />
            </Route>

            <Route
              element={
                <ProtectedRoute roles={['PRODUCT_ADMIN', 'ORG_ADMIN', 'RECEPTIONIST']} />
              }
            >
              <Route path="/staff/bookings" element={<StaffBookingsPage />} />
              <Route path="/staff/rooms" element={<StaffRoomsPage />} />
              <Route path="/staff/cancellations" element={<StaffCancellationsPage />} />
            </Route>

            <Route element={<ProtectedRoute roles={['PRODUCT_ADMIN', 'ORG_ADMIN']} />}>
              <Route path="/staff/team" element={<StaffTeamPage />} />
            </Route>

            <Route element={<ProtectedRoute roles={['PRODUCT_ADMIN']} />}>
              <Route path="/platform/organizations" element={<PlatformOrganizationsPage />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
