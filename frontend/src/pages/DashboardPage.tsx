import { useAuthStore } from '@/hooks/useAuth'
import { useVPSInstances } from '@/hooks/useApi'
import { Card, CardContent, Badge, Skeleton, TableSkeleton } from '@/components/ui'
import { Server, Cpu, HardDrive, Wifi, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { cn, formatBytes, getStatusColor } from '@/utils/helpers'

export function DashboardPage() {
  const { user } = useAuthStore()
  const { data: vpsList, isLoading, error } = useVPSInstances()

  const runningVPS = vpsList?.filter(v => v.status === 'running').length || 0
  const totalVPS = vpsList?.length || 0

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} variant="rectangular" className="h-24" />)}
        </div>
        <TableSkeleton rows={5} columns={6} />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <AlertCircle className="h-12 w-12 text-vex-danger mx-auto mb-4" />
          <h3 className="text-lg font-medium text-vex-text">Failed to load VPS instances</h3>
          <p className="text-vex-textMuted mt-1">Please try again later</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-vex-text">Dashboard</h1>
          <p className="text-vex-textMuted">Welcome back, {user?.username}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-vex-textMuted text-sm">Total VPS</p>
                <p className="text-3xl font-bold text-vex-text">{totalVPS}</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <Server className="h-6 w-6 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-vex-textMuted text-sm">Running</p>
                <p className="text-3xl font-bold text-vex-success">{runningVPS}</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-vex-textMuted text-sm">Stopped</p>
                <p className="text-3xl font-bold text-vex-warning">{totalVPS - runningVPS}</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-yellow-500/10 flex items-center justify-center">
                <XCircle className="h-6 w-6 text-yellow-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-vex-textMuted text-sm">RDP Enabled</p>
                <p className="text-3xl font-bold text-vex-primary">
                  {vpsList?.filter(v => v.rdp_instance?.status === 'online').length || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <Wifi className="h-6 w-6 text-purple-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-vex-border bg-vex-bg">
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">VPS</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">Resources</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">IP Address</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">RDP</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-vex-textMuted uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-vex-border">
                {vpsList?.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-vex-textMuted">
                      No VPS instances yet. <a href="/vps/create" className="text-vex-primary hover:underline">Create your first VPS</a>
                    </td>
                  </tr>
                ) : (
                  vpsList?.map((vps) => (
                    <tr key={vps.id} className="hover:bg-vex-bg/50 transition-colors">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-vex-text">{vps.vps_id}</p>
                          <p className="text-sm text-vex-textMuted">{vps.hostname}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <Badge className={getStatusColor(vps.status)}>
                          {vps.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-4 text-sm text-vex-textMuted">
                          <span className="flex items-center gap-1">
                            <Cpu className="h-4 w-4" /> {vps.cpu} vCPU
                          </span>
                          <span className="flex items-center gap-1">
                            <HardDrive className="h-4 w-4" /> {vps.ram} GB RAM
                          </span>
                          <span className="flex items-center gap-1">
                            <Wifi className="h-4 w-4" /> {vps.storage} GB
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <p className="font-mono text-sm text-vex-text">{vps.ipv4 || 'Pending'}</p>
                        {vps.ipv6 && <p className="font-mono text-xs text-vex-textMuted">{vps.ipv6}</p>}
                      </td>
                      <td className="px-6 py-4">
                        {vps.rdp_instance ? (
                          <Badge className={getStatusColor(vps.rdp_instance.status)}>
                            {vps.rdp_instance.status}
                          </Badge>
                        ) : (
                          <span className="text-vex-textMuted text-sm">Not created</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <a href={`/vps/${vps.id}`} className="text-vex-primary hover:underline text-sm font-medium">
                          Manage
                        </a>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}