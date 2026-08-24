import { useAuthStore } from '@/hooks/useAuth'
import { useAdminDashboard, useAdminUsers, useAdminVPS, useAdminRDP, useAuditLogs } from '@/hooks/useApi'
import { Card, CardContent, Badge, Skeleton, TableSkeleton } from '@/components/ui'
import { Users, Server, Monitor, Database, Activity, Clock, TrendingUp } from 'lucide-react'
import { cn, getStatusColor } from '@/utils/helpers'

export function AdminDashboardPage() {
  const { hasRole } = useAuthStore()
  const { data: stats, isLoading } = useAdminDashboard()
  const { data: users } = useAdminUsers({ page_size: 5 })
  const { data: vpsList } = useAdminVPS({ page_size: 5 })
  const { data: rdpList } = useAdminRDP({ page_size: 5 })
  const { data: auditLogs } = useAuditLogs({ page_size: 10 })

  const isAdmin = hasRole(['admin', 'super_admin'])

  const statCards = [
    { label: 'Total Users', value: stats?.total_users || 0, icon: Users, color: 'text-blue-500', bg: 'bg-blue-500/10' },
    { label: 'Total VPS', value: stats?.total_vps || 0, icon: Server, color: 'text-green-500', bg: 'bg-green-500/10' },
    { label: 'Online VPS', value: stats?.online_vps || 0, icon: TrendingUp, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
    { label: 'RDP Instances', value: stats?.total_rdp || 0, icon: Monitor, color: 'text-purple-500', bg: 'bg-purple-500/10' },
    { label: 'Online RDP', value: stats?.online_rdp || 0, icon: CheckCircle, color: 'text-teal-500', bg: 'bg-teal-500/10' },
    { label: 'Hosts', value: stats?.total_hosts || 0, icon: Database, color: 'text-orange-500', bg: 'bg-orange-500/10' },
    { label: 'Running Jobs', value: stats?.running_jobs || 0, icon: Activity, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
  ]

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {statCards.map((_, i) => <Skeleton key={i} variant="rectangular" className="h-24" />)}
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <TableSkeleton rows={5} columns={4} />
          <TableSkeleton rows={5} columns={4} />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-vex-text">Admin Dashboard</h1>
        <p className="text-vex-textMuted">System overview and quick actions</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        {statCards.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-vex-textMuted text-sm">{stat.label}</p>
                  <p className="text-3xl font-bold text-vex-text">{stat.value}</p>
                </div>
                <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', stat.bg)}>
                  <stat.icon className={cn('h-6 w-6', stat.color)} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent VPS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-vex-border">
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">VPS ID</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Owner</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Status</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Resources</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vex-border">
                  {vpsList?.slice(0, 5).map((vps) => (
                    <tr key={vps.id} className="hover:bg-vex-bg/50">
                      <td className="px-4 py-2 font-mono text-sm text-vex-text">{vps.vps_id}</td>
                      <td className="px-4 py-2 text-sm text-vex-text">{vps.owner}</td>
                      <td className="px-4 py-2"><Badge className={getStatusColor(vps.status)}>{vps.status}</Badge></td>
                      <td className="px-4 py-2 text-sm text-vex-textMuted">{vps.cpu}vCPU / {vps.ram}GB</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent RDP</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-vex-border">
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">VPS</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">User</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Status</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Provider</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vex-border">
                  {rdpList?.slice(0, 5).map((rdp) => (
                    <tr key={rdp.id} className="hover:bg-vex-bg/50">
                      <td className="px-4 py-2 font-mono text-sm text-vex-text">{rdp.vps_id}</td>
                      <td className="px-4 py-2 text-sm text-vex-text">{rdp.owner}</td>
                      <td className="px-4 py-2"><Badge className={getStatusColor(rdp.status)}>{rdp.status}</Badge></td>
                      <td className="px-4 py-2 text-sm text-vex-textMuted">{rdp.tunnel_provider || 'None'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-vex-border">
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Username</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Email</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Role</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-vex-textMuted">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vex-border">
                  {users?.slice(0, 5).map((user) => (
                    <tr key={user.id} className="hover:bg-vex-bg/50">
                      <td className="px-4 py-2 font-medium text-vex-text">{user.username}</td>
                      <td className="px-4 py-2 text-sm text-vex-textMuted">{user.email || 'N/A'}</td>
                      <td className="px-4 py-2"><Badge variant="default">{user.role}</Badge></td>
                      <td className="px-4 py-2">
                        <Badge className={user.is_banned ? 'badge-danger' : user.is_active ? 'badge-success' : 'badge-gray'}>
                          {user.is_banned ? 'Banned' : user.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {auditLogs?.slice(0, 10).map((log) => (
                <div key={log.id} className="flex items-center gap-3 p-3 bg-vex-bg rounded-lg border border-vex-border">
                  <div className="w-8 h-8 rounded-full bg-vex-primary/10 flex items-center justify-center flex-shrink-0">
                    <Clock className="h-4 w-4 text-vex-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-vex-text">{log.action}</p>
                    <p className="text-xs text-vex-textMuted">{log.details || 'No details'}</p>
                  </div>
                  <span className="text-xs text-vex-textMuted whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}