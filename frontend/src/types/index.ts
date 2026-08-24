export type UserRole = 'super_admin' | 'admin' | 'support' | 'read_only' | 'user'

export type VPSStatus = 
  | 'creating' | 'running' | 'stopped' | 'starting' | 'stopping' 
  | 'restarting' | 'rebuilding' | 'deleting' | 'error' | 'suspended' | 'expired' | 'not_found'

export type RDPStatus = 
  | 'not_created' | 'creating' | 'docker_starting' | 'docker_ready' 
  | 'selecting_tunnel' | 'tunnel_creating' | 'ready' | 'online' | 'offline' | 'error' | 'stopping' | 'removing'

export type TunnelProvider = 'trycloudflare' | 'pinggy'
export type TunnelStatus = 'stopped' | 'starting' | 'running' | 'error' | 'reconnecting'

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type JobType = 
  | 'vps_create' | 'vps_delete' | 'vps_rebuild' | 'vps_start' | 'vps_stop' | 'vps_restart'
  | 'rdp_install' | 'rdp_restart' | 'rdp_stop' | 'rdp_remove'
  | 'tunnel_create' | 'tunnel_stop' | 'tunnel_restart' | 'tunnel_change'
  | 'metrics_sync'

export interface User {
  id: number
  username: string
  email: string | null
  role: UserRole
  is_active: boolean
  is_banned: boolean
  theme: string
  two_factor_enabled: boolean
  created_at: string
  last_login: string | null
}

export interface VPSPlan {
  id: number
  name: string
  description: string | null
  cpu: number
  ram: number
  storage: number
  bandwidth: number
  ipv4_count: number
  ipv6_count: number
  price: number
  currency: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OperatingSystem {
  id: number
  name: string
  version: string
  docker_image: string
  display_name: string
  is_active: boolean
  sort_order: number
  created_at: string
}

export interface VPSPortMapping {
  host_port: number
  container_port: number
  protocol: 'tcp' | 'udp'
}

export interface VPSInstance {
  id: number
  vps_id: string
  provider_id: string | null
  token: string
  owner_id: number
  plan_id: number | null
  os_id: number | null
  cpu: number
  ram: number
  storage: number
  bandwidth_limit: number
  hostname: string
  ssh_port: number
  additional_ports: VPSPortMapping[]
  ipv4: string | null
  ipv6: string | null
  status: VPSStatus
  provider_status: string | null
  container_id: string | null
  image_id: string | null
  expires_at: string | null
  expires_days: number
  expires_hours: number
  expires_minutes: number
  uptime_start: string | null
  restart_count: number
  last_restart: string | null
  tags: string[]
  created_at: string
  updated_at: string
}

export interface VPSMetrics {
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  network_in_bytes: number
  network_out_bytes: number
  uptime_seconds: number
  timestamp: string
}

export interface RDPInstance {
  id: number
  vps_id: number
  owner_id: number
  status: RDPStatus
  docker_container_id: string | null
  docker_container_name: string | null
  docker_image: string | null
  internal_host: string
  internal_port: number
  tunnel_provider: TunnelProvider | null
  tunnel_status: TunnelStatus
  tunnel_url: string | null
  last_error: string | null
  created_at: string
  updated_at: string
  last_started_at: string | null
  last_stopped_at: string | null
}

export interface RDPTunnel {
  id: number
  rdp_instance_id: number
  provider: TunnelProvider
  status: TunnelStatus
  public_url: string | null
  process_id: number | null
  process_pid: number | null
  last_error: string | null
  created_at: string
  updated_at: string
}

export interface Job {
  id: number
  job_id: string
  job_type: JobType
  status: JobStatus
  user_id: number | null
  vps_id: number | null
  rdp_id: number | null
  payload: Record<string, unknown>
  result: Record<string, unknown>
  error: string | null
  progress: number
  current_step: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  logs: JobLog[]
}

export interface JobLog {
  id: number
  job_id: number
  message: string
  level: string
  timestamp: string
}

export interface TerminalSession {
  id: number
  session_id: string
  user_id: number
  vps_id: number
  is_admin: boolean
  status: string
  ip_address: string | null
  user_agent: string | null
  created_at: string
  ended_at: string | null
  last_activity: string
}

export interface AuditLog {
  id: number
  user_id: number | null
  vps_id: number | null
  rdp_id: number | null
  action: string
  details: string | null
  ip_address: string | null
  user_agent: string | null
  result: string
  timestamp: string
}

export interface Host {
  id: number
  name: string
  endpoint: string
  provider_type: string
  credentials: Record<string, unknown> | null
  cpu_total: number
  ram_total: number
  storage_total: number
  cpu_used: number
  ram_used: number
  storage_used: number
  vps_count: number
  is_active: boolean
  last_heartbeat: string | null
  created_at: string
  updated_at: string
}

export interface Setting {
  key: string
  value: string | null
  description: string | null
  updated_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface APIError {
  code: string
  message: string
  details?: Record<string, unknown>
}

export interface APIResponse<T> {
  success: boolean
  data?: T
  error?: APIError
}