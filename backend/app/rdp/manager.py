import asyncio
import docker
import logging
import shlex
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from app.core.config import get_settings
from app.providers import get_vps_provider
from app.providers.interface import VPSPowerState

settings = get_settings()
logger = logging.getLogger(__name__)


class RDPState(str, Enum):
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


@dataclass
class RDPInfo:
    state: RDPState
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    internal_port: int = 6080
    tunnel_provider: Optional[str] = None
    tunnel_url: Optional[str] = None
    error: Optional[str] = None


class RDPManager:
    def __init__(self):
        self._docker_client: Optional[docker.DockerClient] = None

    def _get_docker_client(self) -> docker.DockerClient:
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def _get_container_name(self, vps_id: str) -> str:
        return f"{settings.RDP_CONTAINER_PREFIX}{vps_id}"

    async def check_prerequisites(self, provider_id: str) -> Dict[str, Any]:
        provider = get_vps_provider()
        vps_status = await provider.get_vps_status(provider_id)
        if vps_status != VPSPowerState.RUNNING:
            return {"ready": False, "reason": f"VPS is not running (status: {vps_status.value})"}

        vps_info = await provider.get_vps(provider_id)
        if not vps_info:
            return {"ready": False, "reason": "VPS not found"}

        try:
            client = self._get_docker_client()
            container = client.containers.get(provider_id)
            exec_result = container.exec_run(["docker", "version"], demux=True)
            if exec_result.exit_code != 0:
                return {"ready": False, "reason": "Docker not available inside VPS"}

            exec_result = container.exec_run(["docker", "info"], demux=True)
            if exec_result.exit_code != 0:
                return {"ready": False, "reason": "Docker daemon not running inside VPS"}

            return {"ready": True, "vps_info": vps_info}
        except docker.errors.NotFound:
            return {"ready": False, "reason": "VPS container not found"}
        except Exception as e:
            logger.error(f"Prerequisites check failed: {e}")
            return {"ready": False, "reason": f"Check failed: {str(e)}"}

    async def ensure_image(self, provider_id: str) -> bool:
        try:
            provider = get_vps_provider()
            vps_info = await provider.get_vps(provider_id)
            if not vps_info:
                return False

            container = self._get_docker_client().containers.get(provider_id)
            image = settings.RDP_DOCKER_IMAGE

            exec_result = container.exec_run(["docker", "image", "inspect", image], demux=True)
            if exec_result.exit_code == 0:
                return True

            logger.info(f"Pulling RDP image {image} on VPS {provider_id}")
            pull_result = container.exec_run(["docker", "pull", "--platform=linux/amd64", image], demux=True, timeout=300)
            return pull_result.exit_code == 0
        except Exception as e:
            logger.error(f"Failed to ensure image: {e}")
            return False

    async def create_rdp_container(self, provider_id: str, vps_id: str) -> Optional[str]:
        try:
            container_name = self._get_container_name(vps_id)
            client = self._get_docker_client()
            vps_container = client.containers.get(provider_id)

            existing = vps_container.exec_run(["docker", "ps", "-a", "-f", f"name={container_name}", "--format", "{{.ID}}"], demux=True)
            if existing.exit_code == 0 and existing.output[0].decode().strip():
                return existing.output[0].decode().strip()

            cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "--platform=linux/amd64",
                "-p", f"{settings.RDP_INTERNAL_PORT}:{settings.RDP_INTERNAL_PORT}",
                "--restart=unless-stopped",
                settings.RDP_DOCKER_IMAGE
            ]

            exec_result = vps_container.exec_run(cmd, demux=True)
            if exec_result.exit_code != 0:
                stderr = exec_result.output[1].decode() if exec_result.output[1] else ""
                logger.error(f"Failed to create RDP container: {stderr}")
                return None

            container_id = exec_result.output[0].decode().strip()
            return container_id
        except Exception as e:
            logger.error(f"Failed to create RDP container: {e}")
            return None

    async def start_rdp_container(self, provider_id: str, container_id: str) -> bool:
        try:
            vps_container = self._get_docker_client().containers.get(provider_id)
            exec_result = vps_container.exec_run(["docker", "start", container_id], demux=True)
            return exec_result.exit_code == 0
        except Exception as e:
            logger.error(f"Failed to start RDP container: {e}")
            return False

    async def stop_rdp_container(self, provider_id: str, container_id: str) -> bool:
        try:
            vps_container = self._get_docker_client().containers.get(provider_id)
            exec_result = vps_container.exec_run(["docker", "stop", container_id], demux=True)
            return exec_result.exit_code == 0
        except Exception as e:
            logger.error(f"Failed to stop RDP container: {e}")
            return False

    async def remove_rdp_container(self, provider_id: str, container_id: str) -> bool:
        try:
            vps_container = self._get_docker_client().containers.get(provider_id)
            exec_result = vps_container.exec_run(["docker", "rm", "-f", container_id], demux=True)
            return exec_result.exit_code == 0
        except Exception as e:
            logger.error(f"Failed to remove RDP container: {e}")
            return False

    async def check_port_ready(self, provider_id: str, port: int = 6080, max_attempts: int = 30) -> bool:
        for attempt in range(max_attempts):
            try:
                provider = get_vps_provider()
                vps_info = await provider.get_vps(provider_id)
                if not vps_info or not vps_info.ipv4:
                    await asyncio.sleep(1)
                    continue

                sock = asyncio.open_connection(vps_info.ipv4, port)
                try:
                    reader, writer = await asyncio.wait_for(sock, timeout=2.0)
                    writer.close()
                    await writer.wait_closed()
                    return True
                except Exception:
                    pass

                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(1)
        return False

    async def get_container_logs(self, provider_id: str, container_id: str, tail: int = 100) -> str:
        try:
            vps_container = self._get_docker_client().containers.get(provider_id)
            exec_result = vps_container.exec_run(["docker", "logs", "--tail", str(tail), container_id], demux=True)
            stdout = exec_result.output[0].decode() if exec_result.output[0] else ""
            stderr = exec_result.output[1].decode() if exec_result.output[1] else ""
            return stdout + stderr
        except Exception as e:
            logger.error(f"Failed to get container logs: {e}")
            return str(e)

    async def get_container_status(self, provider_id: str, container_id: str) -> Dict[str, Any]:
        try:
            vps_container = self._get_docker_client().containers.get(provider_id)
            exec_result = vps_container.exec_run(["docker", "inspect", container_id], demux=True)
            if exec_result.exit_code != 0:
                return {"exists": False}

            import json
            output = exec_result.output[0].decode() if exec_result.output[0] else "[]"
            data = json.loads(output)
            if not data:
                return {"exists": False}

            container_info = data[0]
            state = container_info.get("State", {})
            return {
                "exists": True,
                "running": state.get("Running", False),
                "status": state.get("Status", "unknown"),
                "exit_code": state.get("ExitCode", 0),
                "started_at": state.get("StartedAt"),
                "finished_at": state.get("FinishedAt"),
            }
        except Exception as e:
            logger.error(f"Failed to get container status: {e}")
            return {"exists": False, "error": str(e)}


rdp_manager = RDPManager()