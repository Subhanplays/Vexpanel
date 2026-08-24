import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { cn } from '@/utils/helpers'

export function MainLayout() {
  return (
    <div className="min-h-screen bg-vex-bg flex">
      <Sidebar />
      <div className="flex-1 flex flex-col lg:pl-0 min-w-0">
        <Header />
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-vex-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-vex-primary">VexPanel</h1>
          <p className="text-vex-textMuted mt-2">VPS & RDP Hosting Panel</p>
        </div>
        <Outlet />
      </div>
    </div>
  )
}

export function DashboardLayout() {
  return (
    <div className="min-h-screen bg-vex-bg">
      <div className="container mx-auto px-4 py-6">
        <Outlet />
      </div>
    </div>
  )
}