import asyncio
import docker
import paramiko
import socket
import uuid
import random
import string
import shlex
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.providers.interface import (
    VPSProvider, VPSConfig, VPSInfo, VPSMetrics, VPSPowerState, CommandResult
)
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class CustomVPSProvider(VPSProvider):
    def __init__(self):
        self._docker_client: Optional[docker.DockerClient] = None
        self._network_name = settings.DOCKER_NETWORK

    def _get_docker_client(self) -> docker.DockerClient:
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    def _get_network(self):
        client = self._get_docker_client()
        try:
            return client.networks.get(self._network_name)
        except docker.errors.NotFound:
            return client.networks.create(self._network_name, driver="bridge")

    def _generate_vps_id(self) -> str:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

    def _generate_token(self) -> str:
        return str(uuid.uuid4())

    def _generate_password(self) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        return ''.join(random.choices(chars, k=20))

    def _find_free_port(self, used_ports: set, start: int = 20000, end: int = 30000) -> int:
        port = random.randint(start, end)
        while port in used_ports:
            port = random.randint(start, end)
        return port

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def create_vps(self, config: VPSConfig, user_id: int) -> VPSInfo:
        vps_id = self._generate_vps_id()
        token = self._generate_token()
        root_password = config.password or self._generate_password()
        hostname = f"{settings.VPS_HOSTNAME_PREFIX}{vps_id}"

        used_ports = set()
        client = self._get_docker_client()
        for container in client.containers.list(all=True):
            if container.attrs.get('HostConfig', {}).get('PortBindings'):
                for bindings in container.attrs['HostConfig']['PortBindings'].values():
                    if bindings:
                        for binding in bindings:
                            if binding.get('HostPort'):
                                used_ports.add(int(binding['HostPort']))

        ssh_port = self._find_free_port(used_ports)

        ports = {'22/tcp': ssh_port}
        if config.additional_ports:
            for port_mapping in config.additional_ports:
                host_p = port_mapping.get('host_port')
                cont_p = port_mapping.get('container_port', 80)
                proto = port_mapping.get('protocol', 'tcp')
                if host_p and host_p not in used_ports:
                    ports[f'{cont_p}/{proto}'] = host_p
                    used_ports.add(host_p)

        cpuset = f"0-{config.cpu-1}" if config.cpu > 1 else "0"
        volume_name = f"vexpanel-{vps_id}"

        try:
            client.volumes.get(volume_name)
        except docker.errors.NotFound:
            client.volumes.create(name=volume_name)

        image_tag = await self._build_custom_image(config.os_image)

        container = await self._run_sync(
            client.containers.run,
            image_tag,
            detach=True,
            privileged=True,
            hostname=hostname,
            mem_limit=f"{config.ram}g",
            nano_cpus=config.cpu * 10**9,
            cpuset_cpus=cpuset,
            cap_add=["SYS_ADMIN", "NET_ADMIN"],
            security_opt=["seccomp=unconfined"],
            network=self._network_name,
            volumes={volume_name: {'bind': '/data', 'mode': 'rw'}},
            restart_policy={"Name": "always"},
            ports=ports,
            name=f"vexpanel-vps-{vps_id}"
        )

        await asyncio.sleep(5)
        container.reload()

        await self._setup_container(container.id, config.ram, vps_id, ssh_port, root_password)

        tmate_session = await self._get_tmate_session(container.id)

        additional_ports_list = []
        if config.additional_ports:
            for pm in config.additional_ports:
                additional_ports_list.append({
                    "host_port": pm.get('host_port'),
                    "container_port": pm.get('container_port', 80),
                    "protocol": pm.get('protocol', 'tcp')
                })

        return VPSInfo(
            vps_id=vps_id,
            provider_id=container.id,
            status=VPSPowerState.RUNNING,
            cpu=config.cpu,
            ram=config.ram,
            storage=config.storage,
            hostname=hostname,
            os_image=config.os_image,
            ssh_port=ssh_port,
            additional_ports=additional_ports_list,
            created_at=datetime.utcnow().isoformat(),
            metadata={
                "token": token,
                "root_password": root_password,
                "tmate_session": tmate_session,
                "container_id": container.id,
                "image_id": image_tag,
                "volume_name": volume_name
            }
        )

    async def _build_custom_image(self, base_image: str) -> str:
        client = self._get_docker_client()
        image_tag = f"vexpanel/{base_image.replace(':', '-').lower()}:latest"

        try:
            client.images.get(image_tag)
            return image_tag
        except docker.errors.ImageNotFound:
            pass

        dockerfile = f"""
FROM {base_image}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \\
    apt-get install -y systemd systemd-sysv dbus sudo \\
                       curl gnupg2 apt-transport-https ca-certificates \\
                       software-properties-common \\
                       docker.io openssh-server tmate && \\
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN mkdir /var/run/sshd && \\
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \\
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
RUN systemctl enable ssh && \\
    systemctl enable docker
RUN apt-get update && \\
    apt-get install -y neofetch htop nano vim wget git tmux net-tools dnsutils iputils-ping ufw \\
                       fail2ban nmap iotop btop wireguard openvpn zabbix-agent glances iftop tcpdump samba apache2 prometheus clamav sysbench && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
"""

        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = os.path.join(tmpdir, 'Dockerfile')
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile)

            image, logs = await self._run_sync(
                client.images.build,
                path=tmpdir,
                tag=image_tag,
                rm=True,
                forcerm=True
            )

        return image_tag

    async def _setup_container(self, container_id: str, memory: int, vps_id: str, ssh_port: int, root_password: str):
        container = self._get_docker_client().containers.get(container_id)
        if container.status != "running":
            container.start()
            await asyncio.sleep(5)

        commands = [
            f"echo 'root:{shlex.quote(root_password)}' | chpasswd",
            f"echo '{settings.VPS_HOSTNAME_PREFIX}{vps_id}' > /etc/hostname && hostname {settings.VPS_HOSTNAME_PREFIX}{vps_id}",
            "systemctl enable fail2ban && systemctl start fail2ban",
            "apt-get update && apt-get upgrade -y",
            "ufw allow 22 && ufw --force enable",
            "apt-get -y autoremove && apt-get clean",
            "chmod 700 /root",
        ]

        for cmd in commands:
            await self._run_docker_command(container_id, ["bash", "-c", cmd])

    async def _run_docker_command(self, container_id: str, command: List[str], timeout: int = 120) -> CommandResult:
        try:
            result = await self._run_sync(
                lambda: self._get_docker_client().containers.get(container_id).exec_run(
                    command, demux=True, timeout=timeout
                )
            )
            stdout = result.output[0].decode() if result.output[0] else ""
            stderr = result.output[1].decode() if result.output[1] else ""
            return CommandResult(
                success=result.exit_code == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=result.exit_code
            )
        except Exception as e:
            return CommandResult(success=False, stdout="", stderr=str(e), exit_code=-1)

    async def _get_tmate_session(self, container_id: str) -> Optional[str]:
        try:
            container = self._get_docker_client().containers.get(container_id)
            exec_result = container.exec_run(["tmate", "-F"], demux=True, tty=True)
            output = exec_result.output[0].decode() if exec_result.output[0] else ""
            for line in output.split('\n'):
                if "ssh session:" in line:
                    return line.split("ssh session:")[1].strip()
        except Exception as e:
            logger.warning(f"Failed to get tmate session: {e}")
        return None

    async def delete_vps(self, provider_id: str) -> bool:
        try:
            client = self._get_docker_client()
            container = client.containers.get(provider_id)
            container.stop(timeout=10)
            container.remove(v=True)
            return True
        except docker.errors.NotFound:
            return True
        except Exception as e:
            logger.error(f"Failed to delete VPS {provider_id}: {e}")
            return False

    async def start_vps(self, provider_id: str) -> bool:
        try:
            container = self._get_docker_client().containers.get(provider_id)
            container.start()
            return True
        except Exception as e:
            logger.error(f"Failed to start VPS {provider_id}: {e}")
            return False

    async def stop_vps(self, provider_id: str) -> bool:
        try:
            container = self._get_docker_client().containers.get(provider_id)
            container.stop(timeout=30)
            return True
        except Exception as e:
            logger.error(f"Failed to stop VPS {provider_id}: {e}")
            return False

    async def restart_vps(self, provider_id: str) -> bool:
        try:
            container = self._get_docker_client().containers.get(provider_id)
            container.restart()
            return True
        except Exception as e:
            logger.error(f"Failed to restart VPS {provider_id}: {e}")
            return False

    async def rebuild_vps(self, provider_id: str, os_image: str) -> bool:
        try:
            client = self._get_docker_client()
            container = client.containers.get(provider_id)

            vps_info = await self.get_vps(provider_id)
            if not vps_info:
                return False

            was_running = container.status == 'running'
            container.stop(timeout=30)
            container.remove(v=True)

            image_tag = await self._build_custom_image(os_image)

            ports = {'22/tcp': vps_info.ssh_port}
            for pm in vps_info.additional_ports or []:
                ports[f"{pm['container_port']}/{pm['protocol']}"] = pm['host_port']

            cpuset = f"0-{vps_info.cpu-1}" if vps_info.cpu > 1 else "0"
            volume_name = f"vexpanel-{vps_info.vps_id}"

            new_container = await self._run_sync(
                client.containers.run,
                image_tag,
                detach=True,
                privileged=True,
                hostname=vps_info.hostname,
                mem_limit=f"{vps_info.ram}g",
                nano_cpus=vps_info.cpu * 10**9,
                cpuset_cpus=cpuset,
                cap_add=["SYS_ADMIN", "NET_ADMIN"],
                security_opt=["seccomp=unconfined"],
                network=self._network_name,
                volumes={volume_name: {'bind': '/data', 'mode': 'rw'}},
                restart_policy={"Name": "always"},
                ports=ports,
                name=f"vexpanel-vps-{vps_info.vps_id}"
            )

            await asyncio.sleep(5)
            new_container.reload()

            root_password = vps_info.metadata.get('root_password') if vps_info.metadata else None
            if not root_password:
                root_password = self._generate_password()

            await self._setup_container(new_container.id, vps_info.ram, vps_info.vps_id, vps_info.ssh_port, root_password)

            return True
        except Exception as e:
            logger.error(f"Failed to rebuild VPS {provider_id}: {e}")
            return False

    async def get_vps(self, provider_id: str) -> Optional[VPSInfo]:
        try:
            container = self._get_docker_client().containers.get(provider_id)
            labels = container.labels or {}
            vps_id = labels.get('vexpanel.vps_id', provider_id[:12])

            port_bindings = container.attrs.get('HostConfig', {}).get('PortBindings', {})
            ssh_port = 22
            additional_ports = []

            for container_port, bindings in port_bindings.items():
                if bindings:
                    host_port = int(bindings[0].get('HostPort', 0))
                    if container_port == '22/tcp':
                        ssh_port = host_port
                    else:
                        proto = container_port.split('/')[1] if '/' in container_port else 'tcp'
                        cont_p = int(container_port.split('/')[0])
                        additional_ports.append({
                            "host_port": host_port,
                            "container_port": cont_p,
                            "protocol": proto
                        })

            return VPSInfo(
                vps_id=vps_id,
                provider_id=container.id,
                status=self._map_container_status(container.status),
                cpu=int(container.attrs.get('HostConfig', {}).get('NanoCpus', 10**9) / 10**9),
                ram=int(container.attrs.get('HostConfig', {}).get('Memory', 1024**3) / 1024**3),
                storage=0,
                hostname=container.attrs.get('Config', {}).get('Hostname', ''),
                os_image=labels.get('vexpanel.os_image', ''),
                ssh_port=ssh_port,
                additional_ports=additional_ports,
                metadata={"container_id": container.id}
            )
        except docker.errors.NotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to get VPS {provider_id}: {e}")
            return None

    def _map_container_status(self, status: str) -> VPSPowerState:
        mapping = {
            'running': VPSPowerState.RUNNING,
            'exited': VPSPowerState.STOPPED,
            'created': VPSPowerState.STOPPED,
            'restarting': VPSPowerState.RESTARTING,
            'paused': VPSPowerState.STOPPED,
            'dead': VPSPowerState.ERROR,
        }
        return mapping.get(status, VPSPowerState.UNKNOWN)

    async def get_vps_status(self, provider_id: str) -> VPSPowerState:
        try:
            container = self._get_docker_client().containers.get(provider_id)
            return self._map_container_status(container.status)
        except docker.errors.NotFound:
            return VPSPowerState.UNKNOWN
        except Exception:
            return VPSPowerState.ERROR

    async def get_vps_metrics(self, provider_id: str) -> VPSMetrics:
        try:
            container = self._get_docker_client().containers.get(provider_id)
            stats = container.stats(stream=False)

            mem_stats = stats['memory_stats']
            cpu_stats = stats['cpu_stats']
            blkio = stats.get('blkio_stats', {})
            net_stats = stats.get('networks', {})

            mem_usage = mem_stats.get('usage', 0)
            mem_limit = mem_stats.get('limit', 1)
            memory_percent = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0

            cpu_usage = 0
            if 'system_cpu_usage' in cpu_stats and cpu_stats['system_cpu_usage'] > 0:
                cpu_delta = cpu_stats['cpu_usage']['total_usage'] - cpu_stats.get('precpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0)
                system_delta = cpu_stats['system_cpu_usage'] - cpu_stats.get('precpu_stats', {}).get('system_cpu_usage', 0)
                if system_delta > 0:
                    cpu_usage = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage'].get('percpu_usage', [1])) * 100

            disk_read = sum(s['value'] for s in blkio.get('io_service_bytes_recursive', []) if s.get('op') == 'Read')
            disk_write = sum(s['value'] for s in blkio.get('io_service_bytes_recursive', []) if s.get('op') == 'Write')

            net_in = sum(i['rx_bytes'] for i in net_stats.values())
            net_out = sum(i['tx_bytes'] for i in net_stats.values())

            return VPSMetrics(
                cpu_percent=round(cpu_usage, 2),
                memory_percent=round(memory_percent, 2),
                disk_percent=0,
                network_in_bytes=net_in,
                network_out_bytes=net_out,
                uptime_seconds=0
            )
        except Exception as e:
            logger.error(f"Failed to get metrics for {provider_id}: {e}")
            return VPSMetrics(cpu_percent=0, memory_percent=0, disk_percent=0, network_in_bytes=0, network_out_bytes=0, uptime_seconds=0)

    async def execute_command(self, provider_id: str, command: str, timeout: int = 30) -> CommandResult:
        cmd_list = shlex.split(command)
        return await self._run_docker_command(provider_id, cmd_list, timeout)

    async def open_console(self, provider_id: str) -> Dict[str, Any]:
        return {
            "type": "docker_exec",
            "container_id": provider_id,
            "command": ["/bin/bash"],
            "websocket_url": f"/api/v1/vps/console/{provider_id}"
        }

    async def list_vps(self) -> List[VPSInfo]:
        client = self._get_docker_client()
        vps_list = []
        for container in client.containers.list(all=True):
            if container.name.startswith("vexpanel-vps-"):
                info = await self.get_vps(container.id)
                if info:
                    vps_list.append(info)
        return vps_list

    async def change_password(self, provider_id: str, new_password: str) -> bool:
        result = await self._run_docker_command(provider_id, ["bash", "-c", f"echo 'root:{shlex.quote(new_password)}' | chpasswd"])
        return result.success

    async def add_port(self, provider_id: str, host_port: int, container_port: int, protocol: str) -> bool:
        try:
            vps_info = await self.get_vps(provider_id)
            if not vps_info:
                return False

            client = self._get_docker_client()
            container = client.containers.get(provider_id)
            was_running = container.status == 'running'
            if was_running:
                container.stop()
            container.remove()

            ports = {'22/tcp': vps_info.ssh_port}
            for pm in vps_info.additional_ports or []:
                ports[f"{pm['container_port']}/{pm['protocol']}"] = pm['host_port']
            ports[f'{container_port}/{protocol}'] = host_port

            cpuset = f"0-{vps_info.cpu-1}" if vps_info.cpu > 1 else "0"
            volume_name = f"vexpanel-{vps_info.vps_id}"
            image_id = vps_info.metadata.get('image_id') if vps_info.metadata else settings.DEFAULT_OS_IMAGE

            new_container = await self._run_sync(
                client.containers.run,
                image_id,
                detach=True,
                privileged=True,
                hostname=vps_info.hostname,
                mem_limit=f"{vps_info.ram}g",
                nano_cpus=vps_info.cpu * 10**9,
                cpuset_cpus=cpuset,
                cap_add=["SYS_ADMIN", "NET_ADMIN"],
                security_opt=["seccomp=unconfined"],
                network=self._network_name,
                volumes={volume_name: {'bind': '/data', 'mode': 'rw'}},
                restart_policy={"Name": "always"},
                ports=ports,
                name=f"vexpanel-vps-{vps_info.vps_id}"
            )

            await asyncio.sleep(5)
            new_container.reload()

            root_password = vps_info.metadata.get('root_password') if vps_info.metadata else None
            await self._setup_container(new_container.id, vps_info.ram, vps_info.vps_id, vps_info.ssh_port, root_password or self._generate_password())

            return True
        except Exception as e:
            logger.error(f"Failed to add port: {e}")
            return False

    async def remove_port(self, provider_id: str, host_port: int) -> bool:
        try:
            vps_info = await self.get_vps(provider_id)
            if not vps_info:
                return False

            client = self._get_docker_client()
            container = client.containers.get(provider_id)
            was_running = container.status == 'running'
            if was_running:
                container.stop()
            container.remove()

            ports = {'22/tcp': vps_info.ssh_port}
            for pm in vps_info.additional_ports or []:
                if pm['host_port'] != host_port:
                    ports[f"{pm['container_port']}/{pm['protocol']}"] = pm['host_port']

            cpuset = f"0-{vps_info.cpu-1}" if vps_info.cpu > 1 else "0"
            volume_name = f"vexpanel-{vps_info.vps_id}"
            image_id = vps_info.metadata.get('image_id') if vps_info.metadata else settings.DEFAULT_OS_IMAGE

            new_container = await self._run_sync(
                client.containers.run,
                image_id,
                detach=True,
                privileged=True,
                hostname=vps_info.hostname,
                mem_limit=f"{vps_info.ram}g",
                nano_cpus=vps_info.cpu * 10**9,
                cpuset_cpus=cpuset,
                cap_add=["SYS_ADMIN", "NET_ADMIN"],
                security_opt=["seccomp=unconfined"],
                network=self._network_name,
                volumes={volume_name: {'bind': '/data', 'mode': 'rw'}},
                restart_policy={"Name": "always"},
                ports=ports,
                name=f"vexpanel-vps-{vps_info.vps_id}"
            )

            await asyncio.sleep(5)
            new_container.reload()

            root_password = vps_info.metadata.get('root_password') if vps_info.metadata else None
            await self._setup_container(new_container.id, vps_info.ram, vps_info.vps_id, vps_info.ssh_port, root_password or self._generate_password())

            return True
        except Exception as e:
            logger.error(f"Failed to remove port: {e}")
            return False