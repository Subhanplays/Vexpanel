import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/hooks/useAuth'
import { useCurrentUser } from '@/hooks/useApi'
import { MainLayout, AuthLayout, DashboardLayout } from '@/components/layout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { VPSListPage } from '@/pages/vps/VPSListPage'
import { VPSDetailPage } from '@/pages/vps/VPSDetailPage'
import { RDPPage } from '@/pages/rdp/RDPPage'
import { AdminDashboardPage } from '@/pages/admin/AdminDashboardPage'
import { AdminUsersPage } from '@/pages/admin/AdminUsersPage'
import { LoadingSpinner } from '@/components/ui'

function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode; allowedRoles?: string[] }) {
  const { user, isAuthenticated } = useAuthStore()
  const { data: currentUser, isLoading } = useCurrentUser()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated || !currentUser) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(currentUser.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['admin', 'super_admin', 'support']}>
      {children}
    </ProtectedRoute>
  )
}

function AppRoutes() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
        <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />} />
      </Route>

      <Route element={<MainLayout />}>
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        } />

        <Route path="/vps" element={
          <ProtectedRoute>
            <VPSListPage />
          </ProtectedRoute>
        } />
        <Route path="/vps/create" element={
          <ProtectedRoute>
            <VPSListPage />
          </ProtectedRoute>
        } />
        <Route path="/vps/:id" element={
          <ProtectedRoute>
            <VPSDetailPage />
          </ProtectedRoute>
        } />

        <Route path="/vps/:vpsId/rdp" element={
          <ProtectedRoute>
            <RDPPage />
          </ProtectedRoute>
        } />

        <Route path="/admin/*" element={
          <AdminRoute>
            <DashboardLayout />
          </AdminRoute>
        }>
          <Route index element={<AdminDashboardPage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="vps" element={<div>Admin VPS</div>} />
          <Route path="rdp" element={<div>Admin RDP</div>} />
          <Route path="hosts" element={<div>Admin Hosts</div>} />
          <Route path="plans" element={<div>Admin Plans</div>} />
          <Route path="operating-systems" element={<div>Admin OS</div>} />
          <Route path="jobs" element={<div>Admin Jobs</div>} />
          <Route path="audit-logs" element={<div>Admin Audit</div>} />
          <Route path="settings" element={<div>Admin Settings</div>} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return <AppRoutes />
}