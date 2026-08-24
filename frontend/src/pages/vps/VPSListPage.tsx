import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Filter, Loader2 } from 'lucide-react'
import { useVPSInstances, useVPSPlans, useOperatingSystems, useCreateVPS } from '@/hooks/useApi'
import { Button, Input, Select, Card, CardContent, Badge, Modal, Skeleton, TableSkeleton } from '@/components/ui'
import { cn, getStatusColor, formatBytes } from '@/utils/helpers'

export function VPSListPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [formData, setFormData] = useState({
    plan_id: '',
    os_id: '',
    cpu: '',
    ram: '',
    storage: '',
    hostname: '',
    password: '',
    expires_days: '30',
  })
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})

  const { data: vpsList, isLoading, error } = useVPSInstances({ status: statusFilter || undefined })
  const { data: plans } = useVPSPlans()
  const { data: operatingSystems } = useOperatingSystems()
  const { mutate: createVPS, isPending: isCreating } = useCreateVPS()

  const filteredVPS = vpsList?.filter(vps =>
    vps.vps_id.toLowerCase().includes(search.toLowerCase()) ||
    vps.hostname.toLowerCase().includes(search.toLowerCase())
  ) || []

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const errors: Record<string, string> = {}
    if (!formData.hostname) errors.hostname = 'Hostname is required'
    if (!formData.plan_id && (!formData.cpu || !formData.ram || !formData.storage)) {
      errors.resources = 'Select a plan or specify custom resources'
    }
    if (!formData.os_id) errors.os_id = 'Operating system is required'

    setFormErrors(errors)
    if (Object.keys(errors).length === 0) {
      createVPS(formData, {
        onSuccess: () => {
          setShowCreateModal(false)
          setFormData({
            plan_id: '',
            os_id: '',
            cpu: '',
            ram: '',
            storage: '',
            hostname: '',
            password: '',
            expires_days: '30',
          })
        },
      })
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton variant="text" width="200" />
          <Skeleton variant="rectangular" width={120} height={40} />
        </div>
        <TableSkeleton rows={5} columns={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-vex-text">VPS Instances</h1>
          <p className="text-vex-textMuted">Manage your virtual private servers</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create VPS
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-vex-textMuted" />
              <Input
                placeholder="Search VPS..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: '', label: 'All Status' },
                { value: 'running', label: 'Running' },
                { value: 'stopped', label: 'Stopped' },
                { value: 'creating', label: 'Creating' },
                { value: 'error', label: 'Error' },
                { value: 'suspended', label: 'Suspended' },
              ]}
              className="w-full sm:w-48"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-vex-border bg-vex-bg">
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">VPS ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">Hostname</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">Plan / Resources</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">IP Address</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">RDP</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">Created</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-vex-textMuted uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-vex-border">
                {filteredVPS.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center text-vex-textMuted">
                      {search || statusFilter ? 'No matching VPS instances' : 'No VPS instances yet. Create your first VPS to get started.'}
                    </td>
                  </tr>
                ) : (
                  filteredVPS.map((vps) => (
                    <tr key={vps.id} className="hover:bg-vex-bg/50 transition-colors">
                      <td className="px-6 py-4 font-mono text-sm text-vex-text">{vps.vps_id}</td>
                      <td className="px-6 py-4">
                        <p className="font-medium text-vex-text">{vps.hostname}</p>
                        <p className="text-xs text-vex-textMuted">{vps.os_id ? `OS: ${vps.os_id}` : 'Custom'}</p>
                      </td>
                      <td className="px-6 py-4">
                        <Badge className={getStatusColor(vps.status)}>{vps.status}</Badge>
                      </td>
                      <td className="px-6 py-4 text-sm text-vex-textMuted">
                        {vps.plan_id ? `Plan: ${vps.plan_id}` : `${vps.cpu} vCPU / ${vps.ram}GB RAM / ${vps.storage}GB`}
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
                      <td className="px-6 py-4 text-sm text-vex-textMuted">
                        {new Date(vps.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link to={`/vps/${vps.id}`} className="text-vex-primary hover:underline text-sm">
                            Manage
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create VPS"
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Hostname"
              value={formData.hostname}
              onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
              error={formErrors.hostname}
              placeholder="my-server"
            />
            <Select
              label="Plan (Optional)"
              value={formData.plan_id}
              onChange={(e) => {
                const plan = plans?.find(p => p.id === parseInt(e.target.value))
                if (plan) {
                  setFormData({
                    ...formData,
                    plan_id: e.target.value,
                    cpu: String(plan.cpu),
                    ram: String(plan.ram),
                    storage: String(plan.storage),
                  })
                } else {
                  setFormData({ ...formData, plan_id: e.target.value })
                }
              }}
              options={[{ value: '', label: 'Custom Resources' }, ...(plans?.map(p => ({ value: String(p.id), label: `${p.name} (${p.cpu}vCPU/${p.ram}GB/${p.storage}GB)` })) || [])]}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Input
              label="CPU (vCPU)"
              type="number"
              value={formData.cpu}
              onChange={(e) => setFormData({ ...formData, cpu: e.target.value })}
              min="1"
              max="128"
            />
            <Input
              label="RAM (GB)"
              type="number"
              value={formData.ram}
              onChange={(e) => setFormData({ ...formData, ram: e.target.value })}
              min="1"
              max="1024"
            />
            <Input
              label="Storage (GB)"
              type="number"
              value={formData.storage}
              onChange={(e) => setFormData({ ...formData, storage: e.target.value })}
              min="10"
              max="10000"
            />
          </div>

          <Select
            label="Operating System"
            value={formData.os_id}
            onChange={(e) => setFormData({ ...formData, os_id: e.target.value })}
            error={formErrors.os_id}
            options={[{ value: '', label: 'Select OS' }, ...(operatingSystems?.map(os => ({ value: String(os.id), label: os.display_name })) || [])]}
          />

          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Root Password (Optional)"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="Leave empty for auto-generated"
            />
            <Input
              label="Expiration (Days)"
              type="number"
              value={formData.expires_days}
              onChange={(e) => setFormData({ ...formData, expires_days: e.target.value })}
              min="1"
              max="365"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-vex-border">
            <Button type="button" variant="secondary" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={isCreating}>
              Create VPS
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}