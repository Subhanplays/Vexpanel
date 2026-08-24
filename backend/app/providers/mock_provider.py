import asyncio
import random
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.providers.interface import (
    VPSProvider, VPSConfig, VPSInfo, VPSMetrics, VPSPowerState, CommandResult
)


class MockVPSProvider(VPSProvider):
    def __init__(self):
        self._vps_store: Dict[str, VPSInfo] = {}
        self._counter = 0

    def _generate_vps_id(self) -> str:
        self._counter += 1
        return f"MOCK-{self._counter:04d}"

    async def create_vps(self, config: VPSConfig, user_id: int) -> VPSInfo:
        vps_id = self._generate_vps_id()
        provider_id = str(uuid.uuid4())

        await asyncio.sleep(0.5)

        info = VPSInfo(
            vps_id=vps_id,
            provider_id=provider_id,
            status=VPSPowerState.RUNNING,
            cpu=config.cpu,
            ram=config.ram,
            storage=config.storage,
            ipv4=f"10.0.0.{self._counter}",
            ipv6=f"2001:db8::{self._counter}",
            hostname=f"mock-{vps_id.lower()}",
            os_image=config.os_image,
            ssh_port=2222 + self._counter,
            additional_ports=config.additional_ports or [],
            created_at=datetime.utcnow().isoformat(),
            metadata={"mock": True, "user_id": user_id}
        )

        self._vps_store[provider_id] = info
        return info

    async def delete_vps(self, provider_id: str) -> bool:
        if provider_id in self._vps_store:
            del self._vps_store[provider_id]
            return True
        return False

    async def start_vps(self, provider_id: str) -> bool:
        if provider_id in self._vps_store:
            self._vps_store[provider_id].status = VPSPowerState.RUNNING
            return True
        return False

    async def stop_vps(self, provider_id: str) -> bool:
        if provider_id in self._vps_store:
            self._vps_store[provider_id].status = VPSPowerState.STOPPED
            return True
        return False

    async def restart_vps(self, provider_id: str) -> bool:
        if provider_id in self._vps_store:
            self._vps_store[provider_id].status = VPSPowerState.RUNNING
            return True
        return False

    async def rebuild_vps(self, provider_id: str, os_image: str) -> bool:
        if provider_id in self._vps_store:
            self._vps_store[provider_id].os_image = os_image
            self._vps_store[provider_id].status = VPSPowerState.RUNNING
            return True
        return False

    async def get_vps(self, provider_id: str) -> Optional[VPSInfo]:
        return self._vps_store.get(provider_id)

    async def get_vps_status(self, provider_id: str) -> VPSPowerState:
        if provider_id in self._vps_store:
            return self._vps_store[provider_id].status
        return VPSPowerState.UNKNOWN

    async def get_vps_metrics(self, provider_id: str) -> VPSMetrics:
        if provider_id in self._vps_store:
            return VPSMetrics(
                cpu_percent=random.uniform(5, 40),
                memory_percent=random.uniform(20, 60),
                disk_percent=random.uniform(10, 50),
                network_in_bytes=random.randint(1000000, 100000000),
                network_out_bytes=random.randint(1000000, 100000000),
                uptime_seconds=random.randint(3600, 86400 * 30)
            )
        return VPSMetrics(cpu_percent=0, memory_percent=0, disk_percent=0, network_in_bytes=0, network_out_bytes=0, uptime_seconds=0)

    async def execute_command(self, provider_id: str, command: str, timeout: int = 30) -> CommandResult:
        if provider_id not in self._vps_store:
            return CommandResult(success=False, stdout="", stderr="VPS not found", exit_code=-1)

        await asyncio.sleep(0.1)

        if "error" in command.lower():
            return CommandResult(success=False, stdout="", stderr="Mock error", exit_code=1)

        return CommandResult(
            success=True,
            stdout=f"Mock output for: {command}\n",
            stderr="",
            exit_code=0
        )

    async def open_console(self, provider_id: str) -> Dict[str, Any]:
        return {
            "type": "mock",
            "container_id": provider_id,
            "command": ["/bin/bash"],
            "websocket_url": f"/mock/console/{provider_id}"
        }

    async def list_vps(self) -> List[VPSInfo]:
        return list(self._vps_store.values())

    async def change_password(self, provider_id: str, new_password: str) -> bool:
        return provider_id in self._vps_store

    async def add_port(self, provider_id: str, host_port: int, container_port: int, protocol: str) -> bool:
        if provider_id in self._vps_store:
            vps = self._vps_store[provider_id]
            if vps.additional_ports is None:
                vps.additional_ports = []
            vps.additional_ports.append({
                "host_port": host_port,
                "container_port": container_port,
                "protocol": protocol
            })
            return True
        return False

    async def remove_port(self, provider_id: str, host_port: int) -> bool:
        if provider_id in self._vps_store:
            vps = self._vps_store[provider_id]
            if vps.additional_ports:
                vps.additional_ports = [p for p in vps.additional_ports if p.get('host_port') != host_port]
            return True
        return False