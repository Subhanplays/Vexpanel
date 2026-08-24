from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey,
    Enum, Index, UniqueConstraint, JSON, BigInteger
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SUPPORT = "support"
    READ_ONLY = "read_only"
    USER = "user"


class VPSStatus(str, PyEnum):
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


class RDPStatus(str, PyEnum):
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


class TunnelProvider(str, PyEnum):
    TRYCLOUDFLARE = "trycloudflare"
    PINGGY = "pinggy"


class TunnelStatus(str, PyEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class JobStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, PyEnum):
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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    theme = Column(String(16), default="dark")
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    vps_instances = relationship("VPSInstance", back_populates="owner")
    rdp_instances = relationship("RDPInstance", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")
    terminal_sessions = relationship("TerminalSession", back_populates="user")
    api_tokens = relationship("APIToken", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"


class VPSPlan(Base):
    __tablename__ = "vps_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    cpu = Column(Integer, nullable=False)
    ram = Column(Integer, nullable=False)
    storage = Column(Integer, nullable=False)
    bandwidth = Column(Integer, default=0)
    ipv4_count = Column(Integer, default=1)
    ipv6_count = Column(Integer, default=0)
    price = Column(Integer, default=0)
    currency = Column(String(3), default="USD")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<VPSPlan {self.name}>"


class OperatingSystem(Base):
    __tablename__ = "operating_systems"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    version = Column(String(32), nullable=False)
    docker_image = Column(String(128), nullable=False)
    display_name = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("name", "version", name="uq_os_name_version"),)

    def __repr__(self):
        return f"<OperatingSystem {self.display_name}>"


class VPSInstance(Base):
    __tablename__ = "vps_instances"

    id = Column(Integer, primary_key=True, index=True)
    vps_id = Column(String(32), unique=True, index=True, nullable=False)
    provider_id = Column(String(128), index=True, nullable=True)
    token = Column(String(64), unique=True, index=True, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("vps_plans.id"), nullable=True)
    os_id = Column(Integer, ForeignKey("operating_systems.id"), nullable=True)

    cpu = Column(Integer, nullable=False)
    ram = Column(Integer, nullable=False)
    storage = Column(Integer, nullable=False)
    bandwidth_limit = Column(Integer, default=0)

    hostname = Column(String(64), nullable=False)
    root_password = Column(String(128), nullable=True)
    ssh_port = Column(Integer, default=22)
    additional_ports = Column(JSON, default=list)

    ipv4 = Column(String(45), nullable=True)
    ipv6 = Column(String(45), nullable=True)

    status = Column(Enum(VPSStatus), default=VPSStatus.CREATING, nullable=False)
    provider_status = Column(String(64), nullable=True)

    container_id = Column(String(128), nullable=True)
    image_id = Column(String(128), nullable=True)

    expires_at = Column(DateTime, nullable=True)
    expires_days = Column(Integer, default=30)
    expires_hours = Column(Integer, default=0)
    expires_minutes = Column(Integer, default=0)

    uptime_start = Column(DateTime, nullable=True)
    restart_count = Column(Integer, default=0)
    last_restart = Column(DateTime, nullable=True)

    tags = Column(JSON, default=list)
    meta_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="vps_instances")
    rdp_instance = relationship("RDPInstance", back_populates="vps", uselist=False)
    metrics = relationship("VPSMetric", back_populates="vps")
    audit_logs = relationship("AuditLog", back_populates="vps")
    terminal_sessions = relationship("TerminalSession", back_populates="vps")

    __table_args__ = (
        Index("ix_vps_owner_status", "owner_id", "status"),
        Index("ix_vps_provider_id", "provider_id"),
    )

    def __repr__(self):
        return f"<VPSInstance {self.vps_id}>"


class RDPInstance(Base):
    __tablename__ = "rdp_instances"

    id = Column(Integer, primary_key=True, index=True)
    vps_id = Column(Integer, ForeignKey("vps_instances.id"), unique=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(Enum(RDPStatus), default=RDPStatus.NOT_CREATED, nullable=False)

    docker_container_id = Column(String(128), nullable=True)
    docker_container_name = Column(String(128), nullable=True)
    docker_image = Column(String(128), nullable=True)

    internal_host = Column(String(64), default="localhost")
    internal_port = Column(Integer, default=6080)

    tunnel_provider = Column(Enum(TunnelProvider), nullable=True)
    tunnel_status = Column(Enum(TunnelStatus), default=TunnelStatus.STOPPED)
    tunnel_url = Column(String(256), nullable=True)

    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_started_at = Column(DateTime, nullable=True)
    last_stopped_at = Column(DateTime, nullable=True)

    vps = relationship("VPSInstance", back_populates="rdp_instance")
    owner = relationship("User", back_populates="rdp_instances")
    tunnels = relationship("RDPTunnel", back_populates="rdp_instance")

    def __repr__(self):
        return f"<RDPInstance vps={self.vps_id} status={self.status}>"


class RDPTunnel(Base):
    __tablename__ = "rdp_tunnels"

    id = Column(Integer, primary_key=True, index=True)
    rdp_instance_id = Column(Integer, ForeignKey("rdp_instances.id"), nullable=False)
    provider = Column(Enum(TunnelProvider), nullable=False)

    status = Column(Enum(TunnelStatus), default=TunnelStatus.STOPPED)
    public_url = Column(String(256), nullable=True)
    process_id = Column(Integer, nullable=True)
    process_pid = Column(Integer, nullable=True)

    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rdp_instance = relationship("RDPInstance", back_populates="tunnels")

    def __repr__(self):
        return f"<RDPTunnel {self.provider} {self.status}>"


class VPSMetric(Base):
    __tablename__ = "vps_metrics"

    id = Column(Integer, primary_key=True, index=True)
    vps_id = Column(Integer, ForeignKey("vps_instances.id"), nullable=False, index=True)

    cpu_percent = Column(Integer, default=0)
    memory_percent = Column(Integer, default=0)
    disk_percent = Column(Integer, default=0)
    network_in_bytes = Column(BigInteger, default=0)
    network_out_bytes = Column(BigInteger, default=0)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    vps = relationship("VPSInstance", back_populates="metrics")

    __table_args__ = (Index("ix_vps_metrics_vps_time", "vps_id", "timestamp"),)

    def __repr__(self):
        return f"<VPSMetric vps={self.vps_id} cpu={self.cpu_percent}%>"


class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    endpoint = Column(String(256), nullable=False)
    provider_type = Column(String(32), default="docker")
    credentials = Column(JSON, nullable=True)

    cpu_total = Column(Integer, default=0)
    ram_total = Column(Integer, default=0)
    storage_total = Column(Integer, default=0)

    cpu_used = Column(Integer, default=0)
    ram_used = Column(Integer, default=0)
    storage_used = Column(Integer, default=0)

    vps_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Host {self.name}>"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    job_type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    vps_id = Column(Integer, ForeignKey("vps_instances.id"), nullable=True)
    rdp_id = Column(Integer, ForeignKey("rdp_instances.id"), nullable=True)

    payload = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    error = Column(Text, nullable=True)
    progress = Column(Integer, default=0)
    current_step = Column(String(128), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job {self.job_id} {self.job_type} {self.status}>"


class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    level = Column(String(16), default="info")
    timestamp = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="logs")

    def __repr__(self):
        return f"<JobLog {self.job_id} {self.level}>"


class TerminalSession(Base):
    __tablename__ = "terminal_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vps_id = Column(Integer, ForeignKey("vps_instances.id"), nullable=False)

    is_admin = Column(Boolean, default=False)
    status = Column(String(32), default="active")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(256), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="terminal_sessions")
    vps = relationship("VPSInstance", back_populates="terminal_sessions")

    def __repr__(self):
        return f"<TerminalSession {self.session_id}>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    vps_id = Column(Integer, ForeignKey("vps_instances.id"), nullable=True, index=True)
    rdp_id = Column(Integer, ForeignKey("rdp_instances.id"), nullable=True, index=True)

    action = Column(String(64), nullable=False, index=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(256), nullable=True)
    result = Column(String(16), default="success")

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")
    vps = relationship("VPSInstance", back_populates="audit_logs")

    __table_args__ = (Index("ix_audit_user_time", "user_id", "timestamp"),)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id}>"


class APIToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    token_hash = Column(String(128), nullable=False)
    scopes = Column(JSON, default=list)
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="api_tokens")

    def __repr__(self):
        return f"<APIToken {self.name}>"


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Setting {self.key}>"