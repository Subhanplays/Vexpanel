from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class VPSPowerState(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    RESTARTING = "restarting"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class VPSConfig:
    cpu: int
    ram: int
    storage: int
    os_image: str
    hostname: str
    ssh_key: Optional[str] = None
    password: Optional[str] = None
    additional_ports: Optional[List[Dict[str, Any]]] = None
    bandwidth_limit: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class VPSInfo:
    vps_id: str
    provider_id: str
    status: VPSPowerState
    cpu: int
    ram: int
    storage: int
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    hostname: str = ""
    os_image: str = ""
    ssh_port: int = 22
    additional_ports: List[Dict[str, Any]] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class VPSMetrics:
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_in_bytes: int
    network_out_bytes: int
    uptime_seconds: int


@dataclass
class CommandResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int


class VPSProvider(ABC):
    @abstractmethod
    async def create_vps(self, config: VPSConfig, user_id: int) -> VPSInfo:
        pass

    @abstractmethod
    async def delete_vps(self, provider_id: str) -> bool:
        pass

    @abstractmethod
    async def start_vps(self, provider_id: str) -> bool:
        pass

    @abstractmethod
    async def stop_vps(self, provider_id: str) -> bool:
        pass

    @abstractmethod
    async def restart_vps(self, provider_id: str) -> bool:
        pass

    @abstractmethod
    async def rebuild_vps(self, provider_id: str, os_image: str) -> bool:
        pass

    @abstractmethod
    async def get_vps(self, provider_id: str) -> Optional[VPSInfo]:
        pass

    @abstractmethod
    async def get_vps_status(self, provider_id: str) -> VPSPowerState:
        pass

    @abstractmethod
    async def get_vps_metrics(self, provider_id: str) -> VPSMetrics:
        pass

    @abstractmethod
    async def execute_command(self, provider_id: str, command: str, timeout: int = 30) -> CommandResult:
        pass

    @abstractmethod
    async def open_console(self, provider_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def list_vps(self) -> List[VPSInfo]:
        pass

    @abstractmethod
    async def change_password(self, provider_id: str, new_password: str) -> bool:
        pass

    @abstractmethod
    async def add_port(self, provider_id: str, host_port: int, container_port: int, protocol: str) -> bool:
        pass

    @abstractmethod
    async def remove_port(self, provider_id: str, host_port: int) -> bool:
        pass