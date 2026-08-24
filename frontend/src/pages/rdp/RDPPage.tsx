import { useParams, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import {
  Monitor, Play, RotateCcw, Wifi, WifiOff, Trash2, Loader2, AlertCircle,
  CheckCircle, XCircle, Terminal, Logs, Settings, ChevronLeft
} from 'lucide-react'
import { useRDPInstance, useCreateRDP, useRDPTunnel, useChangeRDPTunnel, useRestartRDPTunnel, useRDPAction, useRDPLogs } from '@/hooks/useApi'
import { Card, CardContent, CardHeader, CardTitle, Badge, Button, Alert, Modal, Input } from '@/components/ui'
import { cn, getStatusColor, formatDate } from '@/utils/helpers'

export function RDPPage() {
  const { vpsId } = useParams<{ vpsId: string }>()
  const navigate = useNavigate()
  const vpsIdNum = parseInt(vpsId || '0')
  const [showTunnelModal, setShowTunnelModal] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState<'trycloudflare' | 'pinggy'>('trycloudflare')
  const [logs, setLogs] = useState<string>('')
  const [showLogs, setShowLogs] = useState(false)

  const { data: rdp, isLoading, error } = useRDPInstance(vpsIdNum)
  const { mutate: createRDP, isPending: isCreating } = useCreateRDP(vpsIdNum)
  const { mutate: createTunnel } = useRDPTunnel(vpsIdNum)
  const { mutate: changeTunnel } = useChangeRDPTunnel(vpsIdNum)
  const { mutate: restartTunnel } = useRestartRDPTunnel(vpsIdNum)
  const { mutate: rdpAction } = useRDPAction(vpsIdNum)
  const { data: rdpLogs } = useRDPLogs(vpsIdNum)

  const handleCreateRDP = () => {
    createRDP()
  }

  const handleCreateTunnel = (provider: 'trycloudflare' | 'pinggy') => {
    createTunnel(provider, {
      onSuccess: () => setShowTunnelModal(false),
    })
  }

  const handleRestart = () => {
    rdpAction('restart')
  }

  const handleStop = () => {
    rdpAction('stop')
  }

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this RDP instance? This will remove the Docker container and tunnel.')) {
      rdpAction('delete')
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-24 animate-pulse bg-vex-border rounded-xl" />
        <div className="h-64 animate-pulse bg-vex-border rounded-xl" />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <AlertCircle className="h-12 w-12 text-vex-danger mx-auto mb-4" />
          <h3 className="text-lg font-medium text-vex-text">Failed to load RDP instance</h3>
        </CardContent>
      </Card>
    )
  }

  const isReady = rdp?.status === 'ready' || rdp?.status === 'online' || rdp?.status === 'docker_ready' || rdp?.status === 'selecting_tunnel'
  const isDockerReady = ['docker_ready', 'selecting_tunnel', 'tunnel_creating', 'ready', 'online'].includes(rdp?.status || '')
  const isOnline = rdp?.status === 'online'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-vex-text">RDP Desktop</h1>
          <p className="text-vex-textMuted">Browser-accessible Ubuntu desktop environment</p>
        </div>
        <Button variant="secondary" onClick={() => navigate(`/vps/${vpsId}`)}>
          <ChevronLeft className="h-4 w-4 mr-2" />
          Back to VPS
        </Button>
      </div>

      {!rdp || rdp.status === 'not_created' ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Monitor className="h-16 w-16 text-vex-textMuted mx-auto mb-4" />
            <h3 className="text-lg font-medium text-vex-text">No RDP Environment</h3>
            <p className="text-vex-textMuted mt-2 max-w-md mx-auto">
              Create an Ubuntu desktop environment running in Docker on your VPS and access it through your browser.
            </p>
            <Button onClick={handleCreateRDP} className="mt-6" size="lg" loading={isCreating}>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Create RDP
            </Button>
          </CardContent>
        </Card>
      ) : rdp.status === 'creating' || rdp.status === 'docker_starting' ? (
        <Card>
          <CardContent className="p-8">
            <div className="max-w-md mx-auto text-center">
              <Loader2 className="h-12 w-12 text-vex-primary mx-auto mb-4 animate-spin" />
              <h3 className="text-lg font-medium text-vex-text">
                {rdp.status === 'creating' ? 'Creating RDP Environment' : 'Starting Docker Container'}
              </h3>
              <p className="text-vex-textMuted mt-2">This may take a few minutes...</p>
              <div className="mt-6 space-y-3 text-left">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-vex-success" /> Docker checked
                </div>
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-vex-success" /> Image ready
                </div>
                <div className="flex items-center gap-3">
                  <Loader2 className="h-5 w-5 text-vex-primary animate-spin" /> Container starting
                </div>
                <div className="flex items-center gap-3">
                  <AlertCircle className="h-5 w-5 text-vex-textMuted" /> Checking port 6080
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : rdp.status === 'docker_ready' || rdp.status === 'selecting_tunnel' ? (
        <Card>
          <CardContent className="p-8">
            <div className="max-w-md mx-auto text-center">
              <CheckCircle className="h-12 w-12 text-vex-success mx-auto mb-4" />
              <h3 className="text-lg font-medium text-vex-text">Desktop Created Successfully</h3>
              <p className="text-vex-textMuted mt-2">
                The Ubuntu desktop is running on port 6080. Choose a tunnel provider for browser access.
              </p>
              <div className="mt-6 grid gap-4">
                <Button
                  size="lg"
                  className="h-16"
                  onClick={() => { setSelectedProvider('trycloudflare'); setShowTunnelModal(true); }}
                >
                  <Wifi className="h-6 w-6 mr-2" />
                  <div className="text-left">
                    <p className="font-medium">TryCloudflare</p>
                    <p className="text-sm text-vex-textMuted">Free Cloudflare Tunnel</p>
                  </div>
                </Button>
                <Button
                  size="lg"
                  variant="secondary"
                  className="h-16"
                  onClick={() => { setSelectedProvider('pinggy'); setShowTunnelModal(true); }}
                >
                  <WifiOff className="h-6 w-6 mr-2" />
                  <div className="text-left">
                    <p className="font-medium">Pinggy</p>
                    <p className="text-sm text-vex-textMuted">Simple SSH Tunnel</p>
                  </div>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>RDP Status</CardTitle>
              <div className="flex items-center gap-2">
                <Badge className={getStatusColor(rdp.status)}>{rdp.status}</Badge>
                {rdp.tunnel_provider && (
                  <Badge className={getStatusColor(rdp.tunnel_status)} variant="info">
                    {rdp.tunnel_provider} {rdp.tunnel_status}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="p-4 bg-vex-bg rounded-lg border border-vex-border text-center">
                  <div className="text-2xl font-bold text-vex-primary">6080</div>
                  <p className="text-vex-textMuted text-sm">Internal Port</p>
                </div>
                <div className="p-4 bg-vex-bg rounded-lg border border-vex-border text-center">
                  <p className="text-vex-textMuted text-sm">Tunnel Provider</p>
                  <p className="font-medium capitalize">{rdp.tunnel_provider || 'None'}</p>
                </div>
                <div className="p-4 bg-vex-bg rounded-lg border border-vex-border text-center">
                  <p className="text-vex-textMuted text-sm">Status</p>
                  <Badge className={getStatusColor(rdp.tunnel_status)}>{rdp.tunnel_status}</Badge>
                </div>
              </div>

              {rdp.tunnel_url && (
                <div className="p-4 bg-vex-bg rounded-lg border border-vex-border">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-vex-textMuted text-sm">Browser Access URL</p>
                      <p className="font-mono text-vex-text break-all">{rdp.tunnel_url}</p>
                    </div>
                    <Button size="lg" onClick={() => window.open(rdp.tunnel_url, '_blank')}>
                      <Play className="h-4 w-4 mr-2" />
                      Open RDP
                    </Button>
                  </div>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                <Button onClick={handleRestart} disabled={isOnline ? false : true}>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Restart RDP
                </Button>
                <Button variant="secondary" onClick={() => { restartTunnel(); }}>
                  <Wifi className="h-4 w-4 mr-2" />
                  Restart Tunnel
                </Button>
                <Button variant="secondary" onClick={() => setShowTunnelModal(true)}>
                  <Settings className="h-4 w-4 mr-2" />
                  Change Provider
                </Button>
                <Button variant="secondary" onClick={() => { setShowLogs(true); }}>
                  <Logs className="h-4 w-4 mr-2" />
                  View Logs
                </Button>
                <Button variant="danger" onClick={handleStop}>
                  <Square className="h-4 w-4 mr-2" />
                  Stop RDP
                </Button>
                <Button variant="danger" onClick={handleDelete}>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete RDP
                </Button>
              </div>

              {rdp.last_error && (
                <Alert variant="danger">
                  <strong>Error:</strong> {rdp.last_error}
                </Alert>
              )}
            </CardContent>
          </Card>

          {rdp.docker_container_id && (
            <Card>
              <CardHeader>
                <CardTitle>Container Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-vex-textMuted text-sm">Container ID</p>
                    <p className="font-mono text-vex-text">{rdp.docker_container_id.slice(0, 12)}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">Container Name</p>
                    <p className="font-mono text-vex-text">{rdp.docker_container_name}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">Image</p>
                    <p className="text-vex-text">{rdp.docker_image}</p>
                  </div>
                  <div>
                    <p className="text-vex-textMuted text-sm">Created</p>
                    <p className="text-vex-text">{formatDate(rdp.created_at)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Modal isOpen={showTunnelModal} onClose={() => setShowTunnelModal(false)} title="Create Tunnel" description="Select tunnel provider for browser access">
            <div className="space-y-4">
              <div className="grid gap-4">
                <Button
                  size="lg"
                  className="h-16"
                  variant={selectedProvider === 'trycloudflare' ? 'primary' : 'secondary'}
                  onClick={() => setSelectedProvider('trycloudflare')}
                >
                  <Wifi className="h-6 w-6 mr-2" />
                  <div className="text-left">
                    <p className="font-medium">TryCloudflare</p>
                    <p className="text-sm text-vex-textMuted">Free Cloudflare Quick Tunnel</p>
                  </div>
                </Button>
                <Button
                  size="lg"
                  className="h-16"
                  variant={selectedProvider === 'pinggy' ? 'primary' : 'secondary'}
                  onClick={() => setSelectedProvider('pinggy')}
                >
                  <WifiOff className="h-6 w-6 mr-2" />
                  <div className="text-left">
                    <p className="font-medium">Pinggy</p>
                    <p className="text-sm text-vex-textMuted">Simple SSH Tunnel</p>
                  </div>
                </Button>
              </div>
              <div className="flex justify-end gap-2 pt-4 border-t border-vex-border">
                <Button variant="secondary" onClick={() => setShowTunnelModal(false)}>Cancel</Button>
                <Button onClick={() => handleCreateTunnel(selectedProvider)} loading={isCreating}>
                  Create Tunnel
                </Button>
              </div>
            </div>
          </Modal>

          <Modal isOpen={showLogs} onClose={() => setShowLogs(false)} title="RDP Logs" size="xl">
            <div className="h-[500px] overflow-auto p-4 bg-vex-bg rounded-lg border border-vex-border font-mono text-sm whitespace-pre-wrap">
              {rdpLogs || 'No logs available'}
            </div>
          </Modal>
        </div>
      )}
    </div>
  )
}