import { NavLink, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/hooks/useAuth'
import { cn } from '@/utils/helpers'
import {
  LayoutDashboard,
  Server,
  Monitor,
  Terminal,
  Settings,
  Users,
  Database,
  Activity,
  Shield,
  LogOut,
  Menu,
  X,
  ChevronDown,
} from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui'
import { DropdownMenu, DropdownItem, DropdownDivider } from '@/components/ui/Dropdown'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'VPS', href: '/vps', icon: Server },
  { name: 'RDP', href: '/rdp', icon: Monitor },
  { name: 'Terminal', href: '/terminal', icon: Terminal },
]

const adminNavigation = [
  { name: 'Overview', href: '/admin', icon: LayoutDashboard },
  { name: 'Users', href: '/admin/users', icon: Users },
  { name: 'VPS', href: '/admin/vps', icon: Server },
  { name: 'RDP', href: '/admin/rdp', icon: Monitor },
  { name: 'Hosts', href: '/admin/hosts', icon: Database },
  { name: 'Plans', href: '/admin/plans', icon: Shield },
  { name: 'OS Images', href: '/admin/operating-systems', icon: Monitor },
  { name: 'Jobs', href: '/admin/jobs', icon: Activity },
  { name: 'Audit Logs', href: '/admin/audit-logs', icon: Shield },
  { name: 'Settings', href: '/admin/settings', icon: Settings },
]

export function Sidebar() {
  const location = useLocation()
  const { user, hasRole, logout } = useAuthStore()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  const isAdmin = hasRole(['admin', 'super_admin', 'support'])

  return (
    <>
      <button
        className="lg:hidden fixed top-4 left-4 z-50 btn-secondary"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle menu"
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 bg-vex-card border-r border-vex-border transition-all duration-300',
          'flex flex-col',
          isCollapsed ? 'w-16' : 'w-64',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Sidebar"
      >
        <div className="flex h-16 items-center justify-between px-4 border-b border-vex-border">
          {!isCollapsed && (
            <NavLink to="/dashboard" className="font-bold text-xl text-vex-primary">
              VexPanel
            </NavLink>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="lg:hidden p-1 rounded hover:bg-vex-border"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronDown className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1" aria-label="Main navigation">
          {!isCollapsed && (
            <ul className="space-y-1" role="list">
              {navigation.map((item) => (
                <li key={item.name}>
                  <NavLink
                    to={item.href}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                        isActive
                          ? 'bg-vex-primary/10 text-vex-primary'
                          : 'text-vex-textMuted hover:bg-vex-border hover:text-vex-text'
                      )
                    }
                  >
                    <item.icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                    {item.name}
                  </NavLink>
                </li>
              ))}
            </ul>
          )}

          {isAdmin && !isCollapsed && (
            <>
              <hr className="my-4 border-vex-border" />
              <p className="px-3 text-xs font-semibold text-vex-textMuted uppercase tracking-wider">
                Administration
              </p>
              <ul className="space-y-1" role="list">
                {adminNavigation.map((item) => (
                  <li key={item.name}>
                    <NavLink
                      to={item.href}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                          isActive
                            ? 'bg-vex-primary/10 text-vex-primary'
                            : 'text-vex-textMuted hover:bg-vex-border hover:text-vex-text'
                        )
                      }
                    >
                      <item.icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                      {item.name}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </>
          )}
        </nav>

        {!isCollapsed && (
          <div className="p-4 border-t border-vex-border">
            <DropdownMenu align="left">
              <Button variant="ghost" className="w-full justify-start gap-3" size="sm">
                <div className="w-8 h-8 rounded-full bg-vex-primary/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-medium text-vex-primary">
                    {user?.username?.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 text-left min-w-0">
                  <p className="text-sm font-medium text-vex-text truncate">{user?.username}</p>
                  <p className="text-xs text-vex-textMuted truncate capitalize">{user?.role}</p>
                </div>
                <ChevronDown className="h-4 w-4 text-vex-textMuted" />
              </Button>
              <DropdownItem icon={<Settings className="h-4 w-4" />} onClick={() => {}}>
                Profile
              </DropdownItem>
              <DropdownDivider />
              <DropdownItem icon={<LogOut className="h-4 w-4" />} onClick={logout} danger>
                Logout
              </DropdownItem>
            </DropdownMenu>
          )}
        )}
      </aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}
    </>
  )
}