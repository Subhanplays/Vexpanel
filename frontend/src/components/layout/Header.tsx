import { Bell, Moon, Sun, Search, HelpCircle } from 'lucide-react'
import { useAuthStore } from '@/hooks/useAuth'
import { Button } from '@/components/ui'
import { DropdownMenu, DropdownItem, DropdownDivider } from '@/components/ui/Dropdown'

export function Header() {
  const { user, logout } = useAuthStore()

  return (
    <header className="sticky top-0 z-20 bg-vex-card/80 backdrop-blur-sm border-b border-vex-border">
      <div className="flex items-center justify-between h-16 px-4 lg:px-6">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-vex-text hidden sm:block">
            VexPanel
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="relative">
            <Bell className="h-5 w-5" />
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-vex-danger rounded-full" />
          </Button>

          <Button variant="ghost" size="sm" onClick={() => document.documentElement.classList.toggle('dark')}>
            <Sun className="h-5 w-5 dark:hidden" />
            <Moon className="h-5 w-5 hidden dark:block" />
          </Button>

          <DropdownMenu align="right">
            <Button variant="ghost" size="sm" className="gap-2">
              <HelpCircle className="h-5 w-5" />
              <span className="hidden sm:inline">Help</span>
            </Button>
            <DropdownItem>Documentation</DropdownItem>
            <DropdownItem>API Reference</DropdownItem>
            <DropdownDivider />
            <DropdownItem>Support</DropdownItem>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}