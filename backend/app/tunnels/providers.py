import asyncio
import subprocess
import re
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class TunnelState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class TunnelInfo:
    state: TunnelState
    public_url: Optional[str] = None
    process_id: Optional[int] = None
    error: Optional[str] = None


class TunnelProvider(ABC):
    @abstractmethod
    async def create(self, target_host: str, target_port: int, tunnel_id: str) -> TunnelInfo:
        pass

    @abstractmethod
    async def stop(self, tunnel_id: str) -> bool:
        pass

    @abstractmethod
    async def restart(self, tunnel_id: str) -> TunnelInfo:
        pass

    @abstractmethod
    async def get_status(self, tunnel_id: str) -> TunnelInfo:
        pass

    @abstractmethod
    async def get_url(self, tunnel_id: str) -> Optional[str]:
        pass

    @abstractmethod
    async def destroy(self, tunnel_id: str) -> bool:
        pass


class TryCloudflareProvider(TunnelProvider):
    def __init__(self):
        self._processes: Dict[str, subprocess.Popen] = {}
        self._urls: Dict[str, str] = {}
        self._states: Dict[str, TunnelState] = {}

    async def create(self, target_host: str, target_port: int, tunnel_id: str) -> TunnelInfo:
        try:
            self._states[tunnel_id] = TunnelState.STARTING

            cmd = [
                "cloudflared", "tunnel", "--url", f"http://{target_host}:{target_port}",
                "--no-autoupdate", "--protocol", "http2"
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            self._processes[tunnel_id] = process

            url = await self._extract_url(process, tunnel_id)
            if url:
                self._urls[tunnel_id] = url
                self._states[tunnel_id] = TunnelState.RUNNING
                return TunnelInfo(state=TunnelState.RUNNING, public_url=url, process_id=process.pid)
            else:
                self._states[tunnel_id] = TunnelState.ERROR
                return TunnelInfo(state=TunnelState.ERROR, error="Failed to extract tunnel URL", process_id=process.pid)

        except FileNotFoundError:
            self._states[tunnel_id] = TunnelState.ERROR
            return TunnelInfo(state=TunnelState.ERROR, error="cloudflared not installed")
        except Exception as e:
            self._states[tunnel_id] = TunnelState.ERROR
            logger.error(f"TryCloudflare create error: {e}")
            return TunnelInfo(state=TunnelState.ERROR, error=str(e))

    async def _extract_url(self, process: subprocess.Popen, tunnel_id: str) -> Optional[str]:
        try:
            for _ in range(30):
                if process.stdout.at_eof():
                    break
                line = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
                if not line:
                    continue
                line = line.decode().strip()
                logger.debug(f"cloudflared[{tunnel_id}]: {line}")

                match = re.search(r'(https?://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
                if match:
                    return match.group(1)

                if "Connection closed" in line or "ERR" in line.upper():
                    break
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.error(f"Error extracting URL: {e}")
        return None

    async def stop(self, tunnel_id: str) -> bool:
        process = self._processes.get(tunnel_id)
        if process:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            except Exception:
                pass
            self._processes.pop(tunnel_id, None)
            self._states[tunnel_id] = TunnelState.STOPPED
            return True
        return False

    async def restart(self, tunnel_id: str) -> TunnelInfo:
        await self.stop(tunnel_id)
        return await self.create("", 0, tunnel_id)

    async def get_status(self, tunnel_id: str) -> TunnelInfo:
        state = self._states.get(tunnel_id, TunnelState.STOPPED)
        process = self._processes.get(tunnel_id)
        url = self._urls.get(tunnel_id)

        if process and process.returncode is not None:
            state = TunnelState.ERROR
            self._states[tunnel_id] = TunnelState.ERROR

        return TunnelInfo(
            state=state,
            public_url=url,
            process_id=process.pid if process else None
        )

    async def get_url(self, tunnel_id: str) -> Optional[str]:
        return self._urls.get(tunnel_id)

    async def destroy(self, tunnel_id: str) -> bool:
        await self.stop(tunnel_id)
        self._urls.pop(tunnel_id, None)
        self._states.pop(tunnel_id, None)
        return True


class PinggyProvider(TunnelProvider):
    def __init__(self):
        self._processes: Dict[str, subprocess.Popen] = {}
        self._urls: Dict[str, str] = {}
        self._states: Dict[str, TunnelState] = {}

    async def create(self, target_host: str, target_port: int, tunnel_id: str) -> TunnelInfo:
        try:
            self._states[tunnel_id] = TunnelState.STARTING

            token = settings.PINGGY_TOKEN
            if token:
                cmd = [
                    "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ExitOnForwardFailure=yes",
                    "-R", f"0:{target_host}:{target_port}",
                    f"tunnel@{token}@a.pinggy.io"
                ]
            else:
                cmd = [
                    "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ExitOnForwardFailure=yes",
                    "-R", f"0:{target_host}:{target_port}",
                    "tunnel@a.pinggy.io"
                ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            self._processes[tunnel_id] = process

            url = await self._extract_url(process, tunnel_id)
            if url:
                self._urls[tunnel_id] = url
                self._states[tunnel_id] = TunnelState.RUNNING
                return TunnelInfo(state=TunnelState.RUNNING, public_url=url, process_id=process.pid)
            else:
                self._states[tunnel_id] = TunnelState.ERROR
                return TunnelInfo(state=TunnelState.ERROR, error="Failed to extract Pinggy URL", process_id=process.pid)

        except FileNotFoundError:
            self._states[tunnel_id] = TunnelState.ERROR
            return TunnelInfo(state=TunnelState.ERROR, error="ssh not installed")
        except Exception as e:
            self._states[tunnel_id] = TunnelState.ERROR
            logger.error(f"Pinggy create error: {e}")
            return TunnelInfo(state=TunnelState.ERROR, error=str(e))

    async def _extract_url(self, process: subprocess.Popen, tunnel_id: str) -> Optional[str]:
        try:
            for _ in range(30):
                if process.stderr.at_eof():
                    break
                line = await asyncio.wait_for(process.stderr.readline(), timeout=1.0)
                if not line:
                    continue
                line = line.decode().strip()
                logger.debug(f"pinggy[{tunnel_id}]: {line}")

                match = re.search(r'(https?://[a-zA-Z0-9\-]+\.pinggy\.link)', line)
                if match:
                    return match.group(1)

                if "Permission denied" in line or "Connection closed" in line:
                    break
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.error(f"Error extracting Pinggy URL: {e}")
        return None

    async def stop(self, tunnel_id: str) -> bool:
        process = self._processes.get(tunnel_id)
        if process:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            except Exception:
                pass
            self._processes.pop(tunnel_id, None)
            self._states[tunnel_id] = TunnelState.STOPPED
            return True
        return False

    async def restart(self, tunnel_id: str) -> TunnelInfo:
        await self.stop(tunnel_id)
        return await self.create("", 0, tunnel_id)

    async def get_status(self, tunnel_id: str) -> TunnelInfo:
        state = self._states.get(tunnel_id, TunnelState.STOPPED)
        process = self._processes.get(tunnel_id)
        url = self._urls.get(tunnel_id)

        if process and process.returncode is not None:
            state = TunnelState.ERROR
            self._states[tunnel_id] = TunnelState.ERROR

        return TunnelInfo(
            state=state,
            public_url=url,
            process_id=process.pid if process else None
        )

    async def get_url(self, tunnel_id: str) -> Optional[str]:
        return self._urls.get(tunnel_id)

    async def destroy(self, tunnel_id: str) -> bool:
        await self.stop(tunnel_id)
        self._urls.pop(tunnel_id, None)
        self._states.pop(tunnel_id, None)
        return True


class TunnelManager:
    def __init__(self):
        self._providers: Dict[str, TunnelProvider] = {
            "trycloudflare": TryCloudflareProvider(),
            "pinggy": PinggyProvider(),
        }

    def get_provider(self, provider_name: str) -> Optional[TunnelProvider]:
        return self._providers.get(provider_name)

    async def create_tunnel(self, provider_name: str, target_host: str, target_port: int, tunnel_id: str) -> TunnelInfo:
        provider = self.get_provider(provider_name)
        if not provider:
            return TunnelInfo(state=TunnelState.ERROR, error=f"Unknown provider: {provider_name}")
        return await provider.create(target_host, target_port, tunnel_id)

    async def stop_tunnel(self, provider_name: str, tunnel_id: str) -> bool:
        provider = self.get_provider(provider_name)
        if not provider:
            return False
        return await provider.stop(tunnel_id)

    async def restart_tunnel(self, provider_name: str, tunnel_id: str) -> TunnelInfo:
        provider = self.get_provider(provider_name)
        if not provider:
            return TunnelInfo(state=TunnelState.ERROR, error=f"Unknown provider: {provider_name}")
        return await provider.restart(tunnel_id)

    async def get_status(self, provider_name: str, tunnel_id: str) -> TunnelInfo:
        provider = self.get_provider(provider_name)
        if not provider:
            return TunnelInfo(state=TunnelState.ERROR, error=f"Unknown provider: {provider_name}")
        return await provider.get_status(tunnel_id)

    async def get_url(self, provider_name: str, tunnel_id: str) -> Optional[str]:
        provider = self.get_provider(provider_name)
        if not provider:
            return None
        return await provider.get_url(tunnel_id)

    async def cleanup(self):
        for provider in self._providers.values():
            for tunnel_id in list(getattr(provider, '_processes', {}).keys()):
                await provider.destroy(tunnel_id)


tunnel_manager = TunnelManager()