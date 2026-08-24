from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SUPPORT = "support"
    READ_ONLY = "read_only"
    USER = "user"


class VPSStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    RESTARTING = "restarting"
    REBUILDING = "rebuilding"
    DELETING = "deleting"
    ERROR = "error"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"


class RDPStatus(str, Enum):
    NOT_CREATED = "not_created"
    CREATING = "creating"
    DOCKER_STARTING = "docker_starting"
    DOCKER_READY = "docker_ready"
    SELECTING_TUNNEL = "selecting_tunnel"
    TUNNEL_CREATING = "tunnel_creating"
    READY = "ready"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    STOPPING = "stopping"
    REMOVING = "removing"


class TunnelProvider(str, Enum):
    TRYCLOUDFLARE = "trycloudflare"
    PINGGY = "pinggy"


class TunnelStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    VPS_CREATE = "vps_create"
    VPS_DELETE = "vps_delete"
    VPS_REBUILD = "vps_rebuild"
    VPS_START = "vps_start"
    VPS_STOP = "vps_stop"
    VPS_RESTART = "vps_restart"
    RDP_INSTALL = "rdp_install"
    RDP_RESTART = "rdp_restart"
    RDP_STOP = "rdp_stop"
    RDP_REMOVE = "rdp_remove"
    TUNNEL_CREATE = "tunnel_create"
    TUNNEL_STOP = "tunnel_stop"
    TUNNEL_RESTART = "tunnel_restart"
    TUNNEL_CHANGE = "tunnel_change"
    METRICS_SYNC = "metrics_sync"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str = Field(..., min_length=12, max_length=128)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=12, max_length=128)
    role: Optional[UserRole] = None
    theme: Optional[str] = Field(None, pattern="^(light|dark)$")
    is_active: Optional[bool] = None
    is_banned: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_banned: bool
    theme: str
    two_factor_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    sub: Optional[str] = None
    type: str = "access"


class VPSPlanBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    cpu: int = Field(..., gt=0, le=128)
    ram: int = Field(..., gt=0, le=1024)
    storage: int = Field(..., gt=0, le=10000)
    bandwidth: int = Field(0, ge=0)
    ipv4_count: int = Field(1, ge=0, le=10)
    ipv6_count: int = Field(0, ge=0, le=10)
    price: int = Field(0, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    is_active: bool = True


class VPSPlanCreate(VPSPlanBase):
    pass


class VPSPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = None
    cpu: Optional[int] = Field(None, gt=0, le=128)
    ram: Optional[int] = Field(None, gt=0, le=1024)
    storage: Optional[int] = Field(None, gt=0, le=10000)
    bandwidth: Optional[int] = Field(None, ge=0)
    ipv4_count: Optional[int] = Field(None, ge=0, le=10)
    ipv6_count: Optional[int] = Field(None, ge=0, le=10)
    price: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    is_active: Optional[bool] = None


class VPSPlanResponse(VPSPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OperatingSystemBase(BaseModel):
    name: str
    version: str
    docker_image: str
    display_name: str
    is_active: bool = True
    sort_order: int = 0


class OperatingSystemCreate(OperatingSystemBase):
    pass


class OperatingSystemResponse(OperatingSystemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VPSPortMapping(BaseModel):
    host_port: int = Field(..., gt=0, le=65535)
    container_port: int = Field(..., gt=0, le=65535)
    protocol: str = Field("tcp", pattern="^(tcp|udp)$")


class VPSCreate(BaseModel):
    plan_id: Optional[int] = None
    os_id: Optional[int] = None
    cpu: Optional[int] = Field(None, gt=0, le=128)
    ram: Optional[int] = Field(None, gt=0, le=1024)
    storage: Optional[int] = Field(None, gt=0, le=10000)
    os_image: Optional[str] = None
    hostname: str = Field(..., min_length=1, max_length=64)
    ssh_key: Optional[str] = None
    password: Optional[str] = Field(None, min_length=12, max_length=128)
    additional_ports: List[VPSPortMapping] = []
    bandwidth_limit: int = Field(0, ge=0)
    expires_days: int = Field(30, ge=1, le=365)
    expires_hours: int = Field(0, ge=0, le=23)
    expires_minutes: int = Field(0, ge=0, le=59)
    tags: List[str] = []


class VPSUpdate(BaseModel):
    cpu: Optional[int] = Field(None, gt=0, le=128)
    ram: Optional[int] = Field(None, gt=0, le=1024)
    storage: Optional[int] = Field(None, gt=0, le=10000)
    os_image: Optional[str] = None
    additional_ports: Optional[List[VPSPortMapping]] = None
    bandwidth_limit: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = None


class VPSResponse(BaseModel):
    id: int
    vps_id: str
    provider_id: Optional[str]
    token: str
    owner_id: int
    plan_id: Optional[int]
    os_id: Optional[int]
    cpu: int
    ram: int
    storage: int
    bandwidth_limit: int
    hostname: str
    ssh_port: int
    additional_ports: List[VPSPortMapping]
    ipv4: Optional[str]
    ipv6: Optional[str]
    status: VPSStatus
    provider_status: Optional[str]
    container_id: Optional[str]
    image_id: Optional[str]
    expires_at: Optional[datetime]
    expires_days: int
    expires_hours: int
    expires_minutes: int
    uptime_start: Optional[datetime]
    restart_count: int
    last_restart: Optional[datetime]
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VPSMetricsResponse(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_in_bytes: int
    network_out_bytes: int
    uptime_seconds: int
    timestamp: datetime


class VPSActionRequest(BaseModel):
    pass


class VPSRebuildRequest(BaseModel):
    os_image: str


class VPSPasswordChangeRequest(BaseModel):
    password: Optional[str] = Field(None, min_length=12, max_length=128)


class VPSPortRequest(BaseModel):
    host_port: int = Field(..., gt=0, le=65535)
    container_port: int = Field(80, gt=0, le=65535)
    protocol: str = Field("tcp", pattern="^(tcp|udp)$")


class RDPResponse(BaseModel):
    id: int
    vps_id: int
    owner_id: int
    status: RDPStatus
    docker_container_id: Optional[str]
    docker_container_name: Optional[str]
    docker_image: Optional[str]
    internal_host: str
    internal_port: int
    tunnel_provider: Optional[TunnelProvider]
    tunnel_status: TunnelStatus
    tunnel_url: Optional[str]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_started_at: Optional[datetime]
    last_stopped_at: Optional[datetime]

    class Config:
        from_attributes = True


class RDPTunnelCreateRequest(BaseModel):
    provider: TunnelProvider


class RDPTunnelChangeRequest(BaseModel):
    provider: TunnelProvider


class RDPTunnelResponse(BaseModel):
    id: int
    rdp_instance_id: int
    provider: TunnelProvider
    status: TunnelStatus
    public_url: Optional[str]
    process_id: Optional[int]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RDPActionResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None


class JobLogResponse(BaseModel):
    id: int
    message: str
    level: str
    timestamp: datetime


class JobResponse(BaseModel):
    id: int
    job_id: str
    job_type: JobType
    status: JobStatus
    user_id: Optional[int]
    vps_id: Optional[int]
    rdp_id: Optional[int]
    payload: Dict[str, Any]
    result: Dict[str, Any]
    error: Optional[str]
    progress: int
    current_step: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    logs: List[JobLogResponse] = []

    class Config:
        from_attributes = True


class TerminalSessionCreate(BaseModel):
    vps_id: int


class TerminalSessionResponse(BaseModel):
    id: int
    session_id: str
    user_id: int
    vps_id: int
    is_admin: bool
    status: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    ended_at: Optional[datetime]
    last_activity: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    vps_id: Optional[int]
    rdp_id: Optional[int]
    action: str
    details: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    result: str
    timestamp: datetime

    class Config:
        from_attributes = True


class HostBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    endpoint: str
    provider_type: str = "docker"
    credentials: Optional[Dict[str, Any]] = None


class HostCreate(HostBase):
    pass


class HostUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    endpoint: Optional[str] = None
    provider_type: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class HostResponse(HostBase):
    id: int
    cpu_total: int
    ram_total: int
    storage_total: int
    cpu_used: int
    ram_used: int
    storage_used: int
    vps_count: int
    is_active: bool
    last_heartbeat: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingResponse(BaseModel):
    key: str
    value: Optional[str]
    description: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: str


class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any]


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class SetupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str


class SetupResponse(BaseModel):
    success: bool
    message: str