import { useParams, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Play, Square, RotateCcw, Trash2, Key, Plus, Minus, Terminal, FileText,
  Shield, Cpu, HardDrive, Wifi, Monitor, Settings, AlertCircle, CheckCircle
} from 'lucide-react'
import { useVPSInstance, useVPSMetrics, useVPSAction, useChangeVPSPassword, useAddVPSPort, useRemoveVPSPort, useExecuteVPSCommand } from '@/hooks/useApi'
import { Card, CardContent, CardHeader, CardTitle, Badge, Modal, Input, Button, Alert } from '@/components/ui'
import { cn, getStatusColor, formatBytes, formatUptime, formatDate } from '@/utils/helpers'

export function VPSDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const vpsId = parseInt(id || '0')
  const [activeTab, setActiveTab] = useState<'overview' | 'terminal' | 'rdp' | 'network' | 'storage' | 'metrics' | 'activity' | 'settings'>('overview')
  const [showRebuildModal, setShowRebuildModal] = useState(false)
  const [rebuildOS, setRebuildOS] = useState('')
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [showAddPortModal, setShowAddPortModal] = useState(false)
  const [portForm, setPortForm] = useState({ host_port: '', container_port: '80', protocol: 'tcp' })
  const [command, setCommand] = useState('')
  const [commandOutput, setCommandOutput] = useState('')

  const { data: vps, isLoading, error } = useVPSInstance(vpsId)
  const { data: metrics } = useVPSMetrics(vpsId)
  const { mutate: vpsAction, isPending: isActionPending } = useVPSAction(vpsId)
  const { mutate: changePassword } = useChangeVPSPassword(vpsId)
  const { mutate: addPort } = useAddVPSPort(vpsId)
  const { mutate: removePort } = useRemoveVPSPort(vpsId)
  const { mutate: executeCommand } = useExecuteVPSCommand(vpsId)

  const tabs = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'terminal', label: 'Terminal', icon: Terminal },
    { id: 'rdp', label: 'RDP', icon: Monitor },
    { id: 'network', label: 'Network', icon: Wifi },
    { id: 'storage', label: 'Storage', icon: HardDrive },
    { id: 'metrics', label: 'Metrics', icon: Cpu },
    { id: 'activity', label: 'Activity', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-24 animate-pulse bg-vex-border rounded-xl" />)}
        </div>
        <div className="h-96 animate-pulse bg-vex-border rounded-xl" />
      </div>
    )
  }

  if (error || !vps) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <AlertCircle className="h-12 w-12 text-vex-danger mx-auto mb-4" />
          <h3 className="text-lg font-medium text-vex-text">VPS not found</h3>
          <p className="text-vex-textMuted mt-1">The VPS you're looking for doesn't exist</p>
          <Button variant="secondary" onClick={() => navigate('/vps')} className="mt-4">
            Back to VPS List
          </Button>
        </CardContent>
      </Card>
    )
  }

  const handleAction = (action: 'start' | 'stop' | 'restart' | 'rebuild' | 'delete') => {
    if (action === 'rebuild') {
      setShowRebuildModal(true)
      return
    }
    if (action === 'delete' && !window.confirm('Are you sure you want to delete this VPS? This action cannot be undone.')) {
      return
    }
    vpsAction(action)
  }

  const handleChangePassword = () => {
    changePassword(newPassword || undefined, {
      onSuccess: () => setShowPasswordModal(false),
    })
  }

  const handleAddPort = () => {
    addPort({ host_port: parseInt(portForm.host_port), container_port: parseInt(portForm.container_port), protocol: portForm.protocol }, {
      onSuccess: () => {
        setShowAddPortModal(false)
        setPortForm({ host_port: '', container_port: '80', protocol: 'tcp' })
      },
    })
  }

  const handleExecuteCommand = () => {
    executeCommand(command, {
      onSuccess: (data) => {
        setCommandOutput(data.stdout || data.stderr || 'Command executed')
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-vex-text">{vps.vps_id}</h1>
          <p className="text-vex-textMuted">{vps.hostname}</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge className={getStatusColor(vps.status)}>{vps.status}</Badge>
          <Modal isOpen={showRebuildModal} onClose={() => setShowRebuildModal(false)} title="Rebuild VPS" description="This will reinstall the OS and erase all data">
            <div className="space-y-4">
              <Alert variant="danger">
                This will permanently delete all data on the VPS and reinstall the operating system.
              </Alert>
              <Select
                label="Operating System"
                value={rebuildOS}
                onChange={(e) => setRebuildOS(e.target.value)}
                options={[
                  { value: 'ubuntu:22.04', label: 'Ubuntu 22.04' },
                  { value: 'ubuntu:24.04', label: 'Ubuntu 24.04' },
                  { value: 'debian:12', label: 'Debian 12' },
                  { value: 'alpine:latest', label: 'Alpine Linux' },
                ]}
              />
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setShowRebuildModal(false)}>Cancel</Button>
                <Button variant="danger" onClick={() => { handleAction('rebuild'); setShowRebuildModal(false); }}>Rebuild</Button>
              </div>
            </div>
          </Modal>
        </div>
      </div>

      <div className="flex gap-2 border-b border-vex-border overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
              activeTab === tab.id
                ? 'border-vex-primary text-vex-primary'
                : 'border-transparent text-vex-textMuted hover:text-vex-text hover:border-vex-border'
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-vex-textMuted text-sm">CPU</p>
                    <p className="text-2xl font-bold text-vex-text">{vps.cpu} vCPU</p>
                  </div>
                  <Cpu className="h-8 w-8 text-vex-primary" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-vex-textMuted text-sm">RAM</p>
                    <p className="text-2xl font-bold text-vex-text">{vps.ram} GB</p>
                  </div>
                  <HardDrive className="h-8 w-8 text-vex-success" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-vex-textMuted text-sm">Storage</p>
                    <p className="text-2xl font-bold text-vex-text">{vps.storage} GB</p>
                  </div>
                  <Wifi className="h-8 w-8 text-vex-warning" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-vex-textMuted text-sm">Uptime</p>
                    <p className="text-2xl font-bold text-vex-text">
                      {metrics ? formatUptime(metrics.uptime_seconds) : vps.uptime_start ? formatUptime(Math.floor((Date.now() - new Date(vps.uptime_start).getTime()) / 1000)) : 'N/A'}
                    </p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-vex-info" />
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-vex-textMuted text-sm">VPS ID</p>
                    <p className="font-mono text-vex-text">{vps.vps_id}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">Hostname</p>
                    <p className="text-vex-text">{vps.hostname}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">IPv4</p>
                    <p className="font-mono text-vex-text">{vps.ipv4 || 'Not assigned'}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">IPv6</p>
                    <p className="font-mono text-vex-text">{vps.ipv6 || 'Not assigned'}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">SSH Port</p>
                    <p className="text-vex-text">{vps.ssh_port}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">Status</p>
                    <Badge className={getStatusColor(vps.status)}>{vps.status}</Badge>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">Created</p>
                    <p className="text-vex-text">{formatDate(vps.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">Expires</p>
                    <p className="text-vex-text">{vps.expires_at ? formatDate(vps.expires_at) : 'Never'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {metrics ? (
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-vex-textMuted text-sm">CPU Usage</p>
                      <div className="h-2 bg-vex-border rounded-full overflow-hidden">
                        <div className="h-full bg-vex-primary rounded-full transition-all" style={{ width: `${metrics.cpu_percent}%` }} />
                      </div>
                      <p className="text-sm text-vex-text mt-1">{metrics.cpu_percent.toFixed(1)}%</p>
                    </div>
                    <div>
                      <p className="text-vex-textMuted text-sm">Memory Usage</p>
                      <div className="h-2 bg-vex-border rounded-full overflow-hidden">
                        <div className="h-full bg-vex-success rounded-full transition-all" style={{ width: `${metrics.memory_percent}%` }} />
                      </div>
                      <p className="text-sm text-vex-text mt-1">{metrics.memory_percent.toFixed(1)}%</p>
                    </div>
                    <div>
                      <p className="text-vex-textMuted text-sm">Network In</p>
                      <p className="text-vex-text">{formatBytes(metrics.network_in_bytes)}/s</p>
                    </div>
                    <div>
                      <p className="text-vex-textMuted text-sm">Network Out</p>
                      <p className="text-vex-text">{formatBytes(metrics.network_out_bytes)}/s</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-vex-textMuted text-center py-8">Metrics not available</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Additional Ports</CardTitle>
              <Button size="sm" onClick={() => setShowAddPortModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Port
              </Button>
            </CardHeader>
            <CardContent>
              {vps.additional_ports && vps.additional_ports.length > 0 ? (
                <div className="space-y-2">
                  {vps.additional_ports.map((port, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-vex-bg rounded-lg border border-vex-border">
                      <div className="flex items-center gap-4 text-sm">
                        <span className="font-mono text-vex-text">{port.host_port}:{port.container_port}/{port.protocol}</span>
                      </div>
                      <Button variant="danger" size="sm" onClick={() => removePort(port.host_port)}>
                        <Minus className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-vex-textMuted text-center py-8">No additional ports configured</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'terminal' && (
        <Card>
          <CardContent className="p-0">
            <iframe
              src={`/api/v1/terminal/ws/${vpsId}?token=${localStorage.getItem('access_token')}`}
              className="w-full h-[600px] border-0"
              title="Terminal"
            />
          </CardContent>
        </Card>
      )}

      {activeTab === 'rdp' && (
        <Link to={`/vps/${vpsId}/rdp`}>
          <Card>
            <CardContent className="p-6 text-center">
              <Monitor className="h-16 w-16 text-vex-textMuted mx-auto mb-4" />
              <h3 className="text-lg font-medium text-vex-text">RDP Desktop</h3>
              <p className="text-vex-textMuted mt-1">Manage browser-accessible RDP desktop</p>
              <Button className="mt-4">Open RDP Management</Button>
            </CardContent>
          </Card>
        </Link>
      )}

      {activeTab === 'network' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Network Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-vex-textMuted text-sm">IPv4 Address</p>
                  <p className="font-mono text-vex-text">{vps.ipv4 || 'Not assigned'}</p>
                </div>
                <div>
                  <p className="text-vex-textMuted text-sm">IPv6 Address</p>
                  <p className="font-mono text-vex-text">{vps.ipv6 || 'Not assigned'}</p>
                </div>
                <div>
                  <p className="text-vex-textMuted text-sm">SSH Port</p>
                  <p className="text-vex-text">{vps.ssh_port}</p>
                </div>
                <div>
                  <p className="text-vex-textMuted text-sm">Bandwidth Limit</p>
                  <p className="text-vex-text">{vps.bandwidth_limit > 0 ? `${vps.bandwidth_limit} Mbps` : 'Unlimited'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'storage' && (
        <Card>
          <CardHeader>
            <CardTitle>Storage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="p-4 bg-vex-bg rounded-lg border border-vex-border">
                <p className="text-vex-textMuted text-sm">Total Storage</p>
                <p className="text-2xl font-bold text-vex-text">{vps.storage} GB</p>
              </div>
              <div className="p-4 bg-vex-bg rounded-lg border border-vex-border">
                <p className="text-vex-textMuted text-sm">Used</p>
                <p className="text-2xl font-bold text-vex-text">{metrics ? formatBytes(metrics.disk_percent * vps.storage * 1024 * 1024 * 1024 / 100) : 'N/A'}</p>
              </div>
              <div className="p-4 bg-vex-bg rounded-lg border border-vex-border">
                <p className="text-vex-textMuted text-sm">Available</p>
                <p className="text-2xl font-bold text-vex-text">{metrics ? formatBytes(vps.storage * 1024 * 1024 * 1024 - (metrics.disk_percent * vps.storage * 1024 * 1024 * 1024 / 100)) : 'N/A'}</p>
              </div>
            </div>
            <div className="h-2 bg-vex-border rounded-full overflow-hidden">
              <div className="h-full bg-vex-primary rounded-full transition-all" style={{ width: `${metrics?.disk_percent || 0}%` }} />
            </div>
            <p className="text-sm text-vex-textMuted text-center">{metrics?.disk_percent?.toFixed(1) || 0}% used</p>
          </CardContent>
        </Card>
      )}

      {activeTab === 'metrics' && (
        <Card>
          <CardHeader>
            <CardTitle>Real-time Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            {metrics ? (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="p-4 bg-vex-bg rounded-lg border border-vex-border text-center">
                  <p className="text-3xl font-bold text-vex-primary">{metrics.cpu_percent.toFixed(1)}%</p>
                  <p className="text-vex-textMuted text-sm">CPU</p>
                </div>
                <div className="p-4 bg-vex-bg rounded-lg border border-vex-border text-center">
                  <p className="text-3xl font-bold text-vex-success">{metrics.memory_percent.toFixed(1)}%</p>
                  <p className="text-vex-textMuted text-sm">Memory</p>
                </div>
                <div className="p-4 bg-vex-bg rounded-lg border border-vex-border text-center">
                  <p className="text-3xl font-bold text-vex-warning">{formatBytes(metrics.network_in_bytes)}/s</p>
                  <p className="text-vex-textMuted text-sm">Net In</p>
                </div>
                <div className="p-4 bg-vex-bg rounded-lg border border-vex-border text-center">
                  <p className="text-3xl font-bold text-vex-info">{formatBytes(metrics.network_out_bytes)}/s</p>
                  <p className="text-vex-textMuted text-sm">Net Out</p>
                </div>
              </div>
            ) : (
              <p className="text-vex-textMuted text-center py-8">Metrics not available</p>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'activity' && (
        <Card>
          <CardHeader>
            <CardTitle>Activity Log</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-vex-textMuted text-center py-8">Activity log integration coming soon</p>
          </CardContent>
        </Card>
      )}

      {activeTab === 'settings' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>VPS Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-vex-text">Change Root Password</p>
                  <p className="text-vex-textMuted text-sm">Generate a new root password or provide your own</p>
                </div>
                <Button onClick={() => setShowPasswordModal(true)}>Change Password</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Danger Zone</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <div>
                  <p className="font-medium text-red-400">Delete VPS</p>
                  <p className="text-vex-textMuted text-sm">Permanently delete this VPS and all its data</p>
                </div>
                <Button variant="danger" onClick={() => handleAction('delete')}>Delete VPS</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Modal isOpen={showPasswordModal} onClose={() => setShowPasswordModal(false)} title="Change Root Password">
        <div className="space-y-4">
          <Input
            label="New Password (Optional)"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Leave empty for auto-generated"
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowPasswordModal(false)}>Cancel</Button>
            <Button onClick={handleChangePassword}>Change Password</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showAddPortModal} onClose={() => setShowAddPortModal(false)} title="Add Port Mapping">
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Input
              label="Host Port"
              type="number"
              value={portForm.host_port}
              onChange={(e) => setPortForm({ ...portForm, host_port: e.target.value })}
              min="1"
              max="65535"
              required
            />
            <Input
              label="Container Port"
              type="number"
              value={portForm.container_port}
              onChange={(e) => setPortForm({ ...portForm, container_port: e.target.value })}
              min="1"
              max="65535"
            />
            <Select
              label="Protocol"
              value={portForm.protocol}
              onChange={(e) => setPortForm({ ...portForm, protocol: e.target.value })}
              options={[
                { value: 'tcp', label: 'TCP' },
                { value: 'udp', label: 'UDP' },
              ]}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowAddPortModal(false)}>Cancel</Button>
            <Button onClick={handleAddPort}>Add Port</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}