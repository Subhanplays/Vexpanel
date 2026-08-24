import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/utils/api'
import type {
  User,
  VPSInstance,
  VPSPlan,
  OperatingSystem,
  RDPInstance,
  RDPTunnel,
  Job,
  Host,
  Setting,
  VPSMetrics,
  PaginatedResponse,
} from '@/types'

// Auth
export function useCurrentUser() {
  return useQuery({
    queryKey: ['user', 'current'],
    queryFn: async () => {
      const { data } = await api.get<User>('/auth/me')
      return data
    },
    retry: false,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) => {
      const { data } = await api.post<{ access_token: string; token_type: string; expires_in: number }>('/auth/login', credentials)
      return data
    },
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token)
      queryClient.invalidateQueries({ queryKey: ['user', 'current'] })
    },
  })
}

export function useRegister() {
  return useMutation({
    mutationFn: async (userData: { username: string; email: string; password: string }) => {
      const { data } = await api.post<User>('/auth/register', userData)
      return data
    },
  })
}

// VPS Plans
export function useVPSPlans() {
  return useQuery({
    queryKey: ['vps', 'plans'],
    queryFn: async () => {
      const { data } = await api.get<VPSPlan[]>('/admin/plans')
      return data
    },
  })
}

// Operating Systems
export function useOperatingSystems() {
  return useQuery({
    queryKey: ['vps', 'operating-systems'],
    queryFn: async () => {
      const { data } = await api.get<OperatingSystem[]>('/admin/operating-systems')
      return data.filter(os => os.is_active)
    },
  })
}

// VPS Instances
export function useVPSInstances(params?: { status?: string }) {
  return useQuery({
    queryKey: ['vps', 'instances', params],
    queryFn: async () => {
      const { data } = await api.get<VPSInstance[]>('/vps', { params })
      return data
    },
  })
}

export function useVPSInstance(vpsId: number) {
  return useQuery({
    queryKey: ['vps', 'instance', vpsId],
    queryFn: async () => {
      const { data } = await api.get<VPSInstance>(`/vps/${vpsId}`)
      return data
    },
    enabled: !!vpsId,
  })
}

export function useVPSMetrics(vpsId: number) {
  return useQuery({
    queryKey: ['vps', 'metrics', vpsId],
    queryFn: async () => {
      const { data } = await api.get<VPSMetrics>(`/vps/${vpsId}/metrics`)
      return data
    },
    enabled: !!vpsId,
    refetchInterval: 5000,
  })
}

export function useCreateVPS() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (vpsData: any) => {
      const { data } = await api.post<VPSInstance>('/vps', vpsData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vps', 'instances'] })
    },
  })
}

export function useVPSAction(vpsId: number, action: 'start' | 'stop' | 'restart' | 'rebuild' | 'delete') {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload?: any) => {
      const { data } = await api.post(`/vps/${vpsId}/${action}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vps', 'instances'] })
      queryClient.invalidateQueries({ queryKey: ['vps', 'instance', vpsId] })
    },
  })
}

export function useChangeVPSPassword(vpsId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (password?: string) => {
      const { data } = await api.post(`/vps/${vpsId}/password`, { password })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vps', 'instance', vpsId] })
    },
  })
}

export function useAddVPSPort(vpsId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (portData: { host_port: number; container_port: number; protocol: string }) => {
      const { data } = await api.post(`/vps/${vpsId}/ports`, portData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vps', 'instance', vpsId] })
    },
  })
}

export function useRemoveVPSPort(vpsId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (hostPort: number) => {
      const { data } = await api.delete(`/vps/${vpsId}/ports/${hostPort}`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vps', 'instance', vpsId] })
    },
  })
}

export function useExecuteVPSCommand(vpsId: number) {
  return useMutation({
    mutationFn: async (command: string) => {
      const { data } = await api.post(`/vps/${vpsId}/command`, { command })
      return data
    },
  })
}

// RDP
export function useRDPInstance(vpsId: number) {
  return useQuery({
    queryKey: ['rdp', 'instance', vpsId],
    queryFn: async () => {
      const { data } = await api.get<RDPInstance>(`/vps/${vpsId}/rdp`)
      return data
    },
    enabled: !!vpsId,
  })
}

export function useCreateRDP(vpsId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/vps/${vpsId}/rdp`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rdp', 'instance', vpsId] })
    },
  })
}

export function useRDPTunnel(vpsId: number) {
  return useMutation({
    mutationFn: async (provider: 'trycloudflare' | 'pinggy') => {
      const { data } = await api.post(`/vps/${vpsId}/rdp/tunnel`, { provider })
      return data
    },
  })
}

export function useChangeRDPTunnel(vpsId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (provider: 'trycloudflare' | 'pinggy') => {
      const { data } = await api.post(`/vps/${vpsId}/rdp/tunnel/change`, { provider })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rdp', 'instance', vpsId] })
    },
  })
}

export function useRestartRDPTunnel(vpsId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/vps/${vpsId}/rdp/tunnel/restart`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rdp', 'instance', vpsId] })
    },
  })
}

export function useRDPAction(vpsId: number, action: 'restart' | 'stop' | 'delete') {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/vps/${vpsId}/rdp/${action}`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rdp', 'instance', vpsId] })
    },
  })
}

export function useRDPLogs(vpsId: number, tail = 100) {
  return useQuery({
    queryKey: ['rdp', 'logs', vpsId, tail],
    queryFn: async () => {
      const { data } = await api.get<{ logs: string }>(`/vps/${vpsId}/rdp/logs`, { params: { tail } })
      return data.logs
    },
    enabled: !!vpsId,
  })
}

// Jobs
export function useJobs(params?: { status?: string; job_type?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['jobs', params],
    queryFn: async () => {
      const { data } = await api.get<Job[]>('/admin/jobs', { params })
      return data
    },
    refetchInterval: 3000,
  })
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: async () => {
      const { data } = await api.get<Job>(`/admin/jobs/${jobId}`)
      return data
    },
    enabled: !!jobId,
    refetchInterval: 2000,
  })
}

// Admin
export function useAdminDashboard() {
  return useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: async () => {
      const { data } = await api.get('/admin/dashboard')
      return data
    },
    refetchInterval: 10000,
  })
}

export function useAdminUsers(params?: { page?: number; page_size?: number; role?: string; search?: string }) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: async () => {
      const { data } = await api.get<User[]>('/admin/users', { params })
      return data
    },
  })
}

export function useAdminVPS(params?: { page?: number; page_size?: number; status?: string }) {
  return useQuery({
    queryKey: ['admin', 'vps', params],
    queryFn: async () => {
      const { data } = await api.get<any[]>('/admin/vps', { params })
      return data
    },
  })
}

export function useAdminRDP(params?: { page?: number; page_size?: number; status?: string }) {
  return useQuery({
    queryKey: ['admin', 'rdp', params],
    queryFn: async () => {
      const { data } = await api.get<any[]>('/admin/rdp', { params })
      return data
    },
  })
}

export function useAuditLogs(params?: { page?: number; page_size?: number; user_id?: number; action?: string }) {
  return useQuery({
    queryKey: ['admin', 'audit-logs', params],
    queryFn: async () => {
      const { data } = await api.get<any[]>('/admin/audit-logs', { params })
      return data
    },
  })
}