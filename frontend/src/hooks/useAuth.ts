import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, UserRole } from '@/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  setUser: (user: User | null) => void
  logout: () => void
  hasPermission: (permission: string) => boolean
  hasRole: (roles: UserRole[]) => boolean
}

const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  super_admin: ['*'],
  admin: [
    'users.view', 'users.manage',
    'vps.view', 'vps.create', 'vps.manage', 'vps.delete',
    'rdp.view', 'rdp.manage',
    'terminal.user', 'terminal.admin',
    'hosts.view', 'hosts.manage',
    'settings.view', 'settings.manage',
    'audit.view', 'jobs.view', 'jobs.manage',
  ],
  support: [
    'users.view',
    'vps.view', 'vps.manage',
    'rdp.view', 'rdp.manage',
    'terminal.user',
    'hosts.view',
    'settings.view',
    'audit.view', 'jobs.view',
  ],
  read_only: [
    'users.view',
    'vps.view',
    'rdp.view',
    'hosts.view',
    'settings.view',
    'audit.view', 'jobs.view',
  ],
  user: [
    'vps.view', 'vps.create', 'vps.manage',
    'rdp.view', 'rdp.manage',
    'terminal.user',
  ],
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => {
        localStorage.removeItem('access_token')
        set({ user: null, isAuthenticated: false })
      },
      hasPermission: (permission) => {
        const { user } = get()
        if (!user) return false
        if (user.role === 'super_admin') return true
        const permissions = ROLE_PERMISSIONS[user.role] || []
        return permissions.includes('*') || permissions.includes(permission)
      },
      hasRole: (roles) => {
        const { user } = get()
        if (!user) return false
        return roles.includes(user.role)
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
)