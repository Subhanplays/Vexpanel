import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable
from sqlalchemy.orm import Session
from contextlib import contextmanager

from app.database.session import SessionLocal, get_db_context
from app.models import Job, JobLog, JobType, JobStatus, VPSInstance, RDPInstance, RDPStatus, TunnelProvider, TunnelStatus
from app.providers import get_vps_provider
from app.rdp.manager import rdp_manager, RDPState
from app.tunnels.providers import tunnel_manager, TunnelState
from app.core.config import get_settings

settings = get_settings()

JobHandler = Callable[[Job, Session], Awaitable[Dict[str, Any]]]

_job_handlers: Dict[JobType, JobHandler] = {}
_job_queue: asyncio.Queue = asyncio.Queue()
_worker_task: Optional[asyncio.Task] = None


def register_job_handler(job_type: JobType, handler: JobHandler):
    _job_handlers[job_type] = handler


async def enqueue_job(
    job_type: JobType,
    user_id: Optional[int] = None,
    vps_id: Optional[int] = None,
    rdp_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None
) -> str:
    job_id = str(uuid.uuid4())

    with get_db_context() as db:
        job = Job(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.QUEUED,
            user_id=user_id,
            vps_id=vps_id,
            rdp_id=rdp_id,
            payload=payload or {}
        )
        db.add(job)
        db.flush()

    await _job_queue.put(job_id)
    return job_id


async def _add_job_log(db: Session, job_id: int, message: str, level: str = "info"):
    log = JobLog(job_id=job_id, message=message, level=level)
    db.add(log)


async def _update_job_progress(db: Session, job: Job, progress: int, step: str):
    job.progress = progress
    job.current_step = step
    await _add_job_log(db, job.id, f"Progress: {progress}% - {step}")


async def _worker_loop():
    while True:
        try:
            job_id = await _job_queue.get()
            await _process_job(job_id)
        except Exception as e:
            print(f"Worker error: {e}")
            await asyncio.sleep(1)


async def _process_job(job_id_str: str):
    with get_db_context() as db:
        job = db.query(Job).filter(Job.job_id == job_id_str).first()
        if not job:
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        await _add_job_log(db, job.id, f"Job started: {job.job_type.value}")

        handler = _job_handlers.get(job.job_type)
        if not handler:
            job.status = JobStatus.FAILED
            job.error = f"No handler for job type: {job.job_type.value}"
            job.completed_at = datetime.utcnow()
            await _add_job_log(db, job.id, job.error, "error")
            return

        try:
            result = await handler(job, db)
            job.status = JobStatus.COMPLETED
            job.result = result
            job.progress = 100
            job.completed_at = datetime.utcnow()
            await _add_job_log(db, job.id, "Job completed successfully")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            await _add_job_log(db, job.id, f"Job failed: {e}", "error")


async def start_worker():
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker_loop())


async def stop_worker():
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass


# Job Handlers

async def handle_vps_create(job: Job, db: Session) -> Dict[str, Any]:
    payload = job.payload
    config_data = payload.get("config", {})
    vps_db_id = payload.get("vps_db_id")

    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_db_id).first()
    if not vps:
        raise ValueError("VPS record not found")

    from app.providers.interface import VPSConfig, VPSPortMapping
    config = VPSConfig(
        cpu=config_data.get("cpu"),
        ram=config_data.get("ram"),
        storage=config_data.get("storage"),
        os_image=config_data.get("os_image"),
        hostname=config_data.get("hostname"),
        ssh_key=config_data.get("ssh_key"),
        password=config_data.get("password"),
        additional_ports=[VPSPortMapping(**p) for p in config_data.get("additional_ports", [])],
        bandwidth_limit=config_data.get("bandwidth_limit", 0)
    )

    provider = get_vps_provider()
    await _update_job_progress(db, job, 10, "Creating VPS container")
    vps_info = await provider.create_vps(config, job.user_id or 0)

    await _update_job_progress(db, job, 80, "Saving VPS info")
    vps.provider_id = vps_info.provider_id
    vps.status = vps_info.status.value
    vps.ipv4 = vps_info.ipv4
    vps.ipv6 = vps_info.ipv6
    vps.ssh_port = vps_info.ssh_port
    vps.additional_ports = vps_info.additional_ports
    vps.container_id = vps_info.metadata.get("container_id")
    vps.image_id = vps_info.metadata.get("image_id")
    vps.uptime_start = datetime.utcnow()

    if vps_info.metadata:
        vps.root_password = vps_info.metadata.get("root_password")

    return {"provider_id": vps_info.provider_id, "vps_id": vps_info.vps_id}


async def handle_vps_start(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    if not provider_id:
        raise ValueError("provider_id required")

    provider = get_vps_provider()
    await _update_job_progress(db, job, 50, "Starting VPS")
    success = await provider.start_vps(provider_id)

    if success and job.vps_id:
        vps = db.query(VPSInstance).filter(VPSInstance.id == job.vps_id).first()
        if vps:
            vps.status = "running"
            vps.uptime_start = datetime.utcnow()

    return {"success": success}


async def handle_vps_stop(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    if not provider_id:
        raise ValueError("provider_id required")

    provider = get_vps_provider()
    await _update_job_progress(db, job, 50, "Stopping VPS")
    success = await provider.stop_vps(provider_id)

    if success and job.vps_id:
        vps = db.query(VPSInstance).filter(VPSInstance.id == job.vps_id).first()
        if vps:
            vps.status = "stopped"

    return {"success": success}


async def handle_vps_restart(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    if not provider_id:
        raise ValueError("provider_id required")

    provider = get_vps_provider()
    await _update_job_progress(db, job, 30, "Restarting VPS")
    success = await provider.restart_vps(provider_id)

    if success and job.vps_id:
        vps = db.query(VPSInstance).filter(VPSInstance.id == job.vps_id).first()
        if vps:
            vps.status = "running"
            vps.restart_count = (vps.restart_count or 0) + 1
            vps.last_restart = datetime.utcnow()
            vps.uptime_start = datetime.utcnow()

    return {"success": success}


async def handle_vps_delete(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    if not provider_id:
        raise ValueError("provider_id required")

    provider = get_vps_provider()
    await _update_job_progress(db, job, 50, "Deleting VPS")
    success = await provider.delete_vps(provider_id)

    if success and job.vps_id:
        vps = db.query(VPSInstance).filter(VPSInstance.id == job.vps_id).first()
        if vps:
            db.delete(vps)

    return {"success": success}


async def handle_vps_rebuild(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    os_image = job.payload.get("os_image")
    if not provider_id or not os_image:
        raise ValueError("provider_id and os_image required")

    provider = get_vps_provider()
    await _update_job_progress(db, job, 30, "Rebuilding VPS")
    success = await provider.rebuild_vps(provider_id, os_image)

    if success and job.vps_id:
        vps = db.query(VPSInstance).filter(VPSInstance.id == job.vps_id).first()
        if vps:
            vps.status = "running"
            vps.os_image = os_image
            vps.uptime_start = datetime.utcnow()

    return {"success": success}


async def handle_rdp_install(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    vps_db_id = payload.get("vps_db_id")

    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_db_id).first()
    if not vps:
        raise ValueError("VPS not found")

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        raise ValueError("RDP record not found")

    provider = get_vps_provider()

    await _update_job_progress(db, job, 10, "Checking VPS status")
    prereqs = await rdp_manager.check_prerequisites(provider_id)
    if not prereqs.get("ready"):
        raise ValueError(f"Prerequisites not met: {prereqs.get('reason')}")

    await _update_job_progress(db, job, 20, "Ensuring Docker image")
    rdp.status = RDPStatus.DOCKER_STARTING
    image_ok = await rdp_manager.ensure_image(provider_id)
    if not image_ok:
        raise ValueError("Failed to pull RDP Docker image")

    await _update_job_progress(db, job, 40, "Creating RDP container")
    container_id = await rdp_manager.create_rdp_container(provider_id, vps.vps_id)
    if not container_id:
        raise ValueError("Failed to create RDP container")

    rdp.docker_container_id = container_id
    rdp.docker_container_name = f"vexpanel-rdp-{vps.vps_id}"
    rdp.status = RDPStatus.DOCKER_READY

    await _update_job_progress(db, job, 60, "Starting RDP container")
    start_ok = await rdp_manager.start_rdp_container(provider_id, container_id)
    if not start_ok:
        raise ValueError("Failed to start RDP container")

    await _update_job_progress(db, job, 80, "Verifying port 6080")
    port_ready = await rdp_manager.check_port_ready(provider_id, 6080)
    if not port_ready:
        raise ValueError("RDP port 6080 not responding")

    rdp.status = RDPStatus.SELECTING_TUNNEL
    rdp.last_started_at = datetime.utcnow()

    return {"container_id": container_id, "status": "ready_for_tunnel"}


async def handle_rdp_restart(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    if not provider_id:
        raise ValueError("provider_id required")

    rdp = db.query(RDPInstance).filter(RDPInstance.id == job.rdp_id).first()
    if not rdp or not rdp.docker_container_id:
        raise ValueError("RDP container not found")

    await _update_job_progress(db, job, 30, "Stopping RDP container")
    await rdp_manager.stop_rdp_container(provider_id, rdp.docker_container_id)

    await _update_job_progress(db, job, 60, "Starting RDP container")
    await rdp_manager.start_rdp_container(provider_id, rdp.docker_container_id)

    await _update_job_progress(db, job, 80, "Verifying port 6080")
    port_ready = await rdp_manager.check_port_ready(provider_id, rdp.internal_port)
    if not port_ready:
        raise ValueError("RDP port not responding after restart")

    if rdp.tunnel_provider:
        await _update_job_progress(db, job, 90, "Restarting tunnel")
        provider = tunnel_manager.get_provider(rdp.tunnel_provider.value)
        if provider:
            tunnel_id = f"rdp-{rdp.id}"
            await provider.restart(tunnel_id)

    rdp.status = RDPStatus.ONLINE
    rdp.last_started_at = datetime.utcnow()

    return {"success": True}


async def handle_rdp_stop(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    if not provider_id:
        raise ValueError("provider_id required")

    rdp = db.query(RDPInstance).filter(RDPInstance.id == job.rdp_id).first()
    if not rdp or not rdp.docker_container_id:
        raise ValueError("RDP container not found")

    await _update_job_progress(db, job, 50, "Stopping RDP container")
    await rdp_manager.stop_rdp_container(provider_id, rdp.docker_container_id)

    if rdp.tunnel_provider:
        provider = tunnel_manager.get_provider(rdp.tunnel_provider.value)
        if provider:
            tunnel_id = f"rdp-{rdp.id}"
            await provider.stop(tunnel_id)

    rdp.status = RDPStatus.OFFLINE
    rdp.tunnel_status = TunnelStatus.STOPPED
    rdp.tunnel_url = None
    rdp.last_stopped_at = datetime.utcnow()

    return {"success": True}


async def handle_rdp_remove(job: Job, db: Session) -> Dict[str, Any]:
    provider_id = job.payload.get("provider_id")
    if not provider_id:
        raise ValueError("provider_id required")

    rdp = db.query(RDPInstance).filter(RDPInstance.id == job.rdp_id).first()
    if not rdp:
        raise ValueError("RDP not found")

    await _update_job_progress(db, job, 20, "Stopping tunnel")
    if rdp.tunnel_provider:
        provider = tunnel_manager.get_provider(rdp.tunnel_provider.value)
        if provider:
            tunnel_id = f"rdp-{rdp.id}"
            await provider.destroy(tunnel_id)

    await _update_job_progress(db, job, 50, "Removing RDP container")
    if rdp.docker_container_id:
        await rdp_manager.remove_rdp_container(provider_id, rdp.docker_container_id)

    rdp.status = RDPStatus.NOT_CREATED
    rdp.docker_container_id = None
    rdp.docker_container_name = None
    rdp.tunnel_provider = None
    rdp.tunnel_status = TunnelStatus.STOPPED
    rdp.tunnel_url = None

    return {"success": True}


async def handle_tunnel_create(job: Job, db: Session) -> Dict[str, Any]:
    provider_name = job.payload.get("provider")
    provider_id = job.payload.get("provider_id")
    internal_port = job.payload.get("internal_port", 6080)

    if not provider_name or not provider_id:
        raise ValueError("provider and provider_id required")

    provider = get_vps_provider()
    vps_info = await provider.get_vps(provider_id)
    if not vps_info or not vps_info.ipv4:
        raise ValueError("Cannot determine VPS IP address")

    tunnel_id = f"rdp-{job.rdp_id}"
    await _update_job_progress(db, job, 30, f"Creating {provider_name} tunnel")

    tunnel_info = await tunnel_manager.create_tunnel(provider_name, vps_info.ipv4, internal_port, tunnel_id)

    rdp = db.query(RDPInstance).filter(RDPInstance.id == job.rdp_id).first()
    if rdp:
        rdp.tunnel_provider = TunnelProvider(provider_name)
        rdp.tunnel_status = tunnel_info.state
        rdp.tunnel_url = tunnel_info.public_url
        if tunnel_info.state == TunnelState.RUNNING:
            rdp.status = RDPStatus.ONLINE
        elif tunnel_info.state == TunnelState.ERROR:
            rdp.status = RDPStatus.ERROR
            rdp.last_error = tunnel_info.error

        tunnel_record = RDPTunnel(
            rdp_instance_id=rdp.id,
            provider=TunnelProvider(provider_name),
            status=tunnel_info.state,
            public_url=tunnel_info.public_url,
            process_id=tunnel_info.process_id,
            last_error=tunnel_info.error
        )
        db.add(tunnel_record)

    return {"tunnel_url": tunnel_info.public_url, "state": tunnel_info.state.value}


async def handle_tunnel_change(job: Job, db: Session) -> Dict[str, Any]:
    new_provider_name = job.payload.get("new_provider")
    provider_id = job.payload.get("provider_id")
    internal_port = job.payload.get("internal_port", 6080)

    if not new_provider_name or not provider_id:
        raise ValueError("new_provider and provider_id required")

    rdp = db.query(RDPInstance).filter(RDPInstance.id == job.rdp_id).first()
    if not rdp:
        raise ValueError("RDP not found")

    old_provider_name = rdp.tunnel_provider.value if rdp.tunnel_provider else None

    await _update_job_progress(db, job, 30, "Stopping old tunnel")
    if old_provider_name:
        await tunnel_manager.stop_tunnel(old_provider_name, f"rdp-{rdp.id}")

    provider = get_vps_provider()
    vps_info = await provider.get_vps(provider_id)
    if not vps_info or not vps_info.ipv4:
        raise ValueError("Cannot determine VPS IP address")

    tunnel_id = f"rdp-{rdp.id}"
    await _update_job_progress(db, job, 60, f"Creating {new_provider_name} tunnel")
    tunnel_info = await tunnel_manager.create_tunnel(new_provider_name, vps_info.ipv4, internal_port, tunnel_id)

    rdp.tunnel_provider = TunnelProvider(new_provider_name)
    rdp.tunnel_status = tunnel_info.state
    rdp.tunnel_url = tunnel_info.public_url
    if tunnel_info.state == TunnelState.RUNNING:
        rdp.status = RDPStatus.ONLINE
    elif tunnel_info.state == TunnelState.ERROR:
        rdp.status = RDPStatus.ERROR
        rdp.last_error = tunnel_info.error

    tunnel_record = RDPTunnel(
        rdp_instance_id=rdp.id,
        provider=TunnelProvider(new_provider_name),
        status=tunnel_info.state,
        public_url=tunnel_info.public_url,
        process_id=tunnel_info.process_id,
        last_error=tunnel_info.error
    )
    db.add(tunnel_record)

    return {"tunnel_url": tunnel_info.public_url, "state": tunnel_info.state.value}


async def handle_tunnel_restart(job: Job, db: Session) -> Dict[str, Any]:
    provider_name = job.payload.get("provider")
    provider_id = job.payload.get("provider_id")
    internal_port = job.payload.get("internal_port", 6080)

    if not provider_name or not provider_id:
        raise ValueError("provider and provider_id required")

    rdp = db.query(RDPInstance).filter(RDPInstance.id == job.rdp_id).first()
    if not rdp:
        raise ValueError("RDP not found")

    await _update_job_progress(db, job, 50, "Restarting tunnel")
    tunnel_info = await tunnel_manager.restart_tunnel(provider_name, f"rdp-{rdp.id}")

    rdp.tunnel_status = tunnel_info.state
    rdp.tunnel_url = tunnel_info.public_url
    if tunnel_info.state == TunnelState.RUNNING:
        rdp.status = RDPStatus.ONLINE
    elif tunnel_info.state == TunnelState.ERROR:
        rdp.status = RDPStatus.ERROR
        rdp.last_error = tunnel_info.error

    return {"tunnel_url": tunnel_info.public_url, "state": tunnel_info.state.value}


# Register handlers
register_job_handler(JobType.VPS_CREATE, handle_vps_create)
register_job_handler(JobType.VPS_START, handle_vps_start)
register_job_handler(JobType.VPS_STOP, handle_vps_stop)
register_job_handler(JobType.VPS_RESTART, handle_vps_restart)
register_job_handler(JobType.VPS_DELETE, handle_vps_delete)
register_job_handler(JobType.VPS_REBUILD, handle_vps_rebuild)
register_job_handler(JobType.RDP_INSTALL, handle_rdp_install)
register_job_handler(JobType.RDP_RESTART, handle_rdp_restart)
register_job_handler(JobType.RDP_STOP, handle_rdp_stop)
register_job_handler(JobType.RDP_REMOVE, handle_rdp_remove)
register_job_handler(JobType.TUNNEL_CREATE, handle_tunnel_create)
register_job_handler(JobType.TUNNEL_CHANGE, handle_tunnel_change)
register_job_handler(JobType.TUNNEL_RESTART, handle_tunnel_restart)