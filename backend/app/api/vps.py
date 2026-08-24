from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.database.session import get_db
from app.models import VPSInstance, VPSPlan, OperatingSystem, VPSStatus, User, UserRole
from app.schemas import (
    VPSCreate, VPSUpdate, VPSResponse, VPSMetricsResponse,
    VPSRebuildRequest, VPSPasswordChangeRequest, VPSPortRequest,
    VPSActionResponse, JobResponse
)
from app.auth.security import get_current_active_user, require_permissions
from app.providers import get_vps_provider
from app.providers.interface import VPSConfig, VPSPortMapping
from app.jobs.queue import enqueue_job, JobType

router = APIRouter(prefix="/vps", tags=["vps"])


@router.get("", response_model=List[VPSResponse])
async def list_vps(
    status_filter: Optional[VPSStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(VPSInstance).filter(VPSInstance.owner_id == current_user.id)
    if status_filter:
        query = query.filter(VPSInstance.status == status_filter)
    return query.order_by(VPSInstance.created_at.desc()).all()


@router.get("/{vps_id}", response_model=VPSResponse)
async def get_vps(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT]:
        raise HTTPException(status_code=403, detail="Access denied")

    return vps


@router.post("", response_model=VPSResponse, status_code=status.HTTP_201_CREATED)
async def create_vps(
    vps_data: VPSCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user_vps_count = db.query(VPSInstance).filter(VPSInstance.owner_id == current_user.id).count()
    if user_vps_count >= 3 and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Maximum VPS limit reached")

    plan = None
    if vps_data.plan_id:
        plan = db.query(VPSPlan).filter(VPSPlan.id == vps_data.plan_id, VPSPlan.is_active == True).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found or inactive")
        cpu, ram, storage = plan.cpu, plan.ram, plan.storage
    else:
        if not all([vps_data.cpu, vps_data.ram, vps_data.storage]):
            raise HTTPException(status_code=400, detail="CPU, RAM, and storage required when no plan selected")
        cpu, ram, storage = vps_data.cpu, vps_data.ram, vps_data.storage

    os_image = vps_data.os_image
    if vps_data.os_id:
        os_obj = db.query(OperatingSystem).filter(OperatingSystem.id == vps_data.os_id, OperatingSystem.is_active == True).first()
        if not os_obj:
            raise HTTPException(status_code=404, detail="Operating system not found or inactive")
        os_image = os_obj.docker_image
    elif not os_image:
        from app.core.config import get_settings
        os_image = get_settings().DEFAULT_OS_IMAGE

    vps_id = f"VPS-{''.join(str(uuid.uuid4().int)[:8])}"
    token = str(uuid.uuid4())

    vps = VPSInstance(
        vps_id=vps_id,
        token=token,
        owner_id=current_user.id,
        plan_id=vps_data.plan_id,
        os_id=vps_data.os_id,
        cpu=cpu,
        ram=ram,
        storage=storage,
        bandwidth_limit=vps_data.bandwidth_limit,
        hostname=vps_data.hostname,
        ssh_port=22,
        additional_ports=[p.model_dump() for p in vps_data.additional_ports],
        status=VPSStatus.CREATING,
        expires_days=vps_data.expires_days,
        expires_hours=vps_data.expires_hours,
        expires_minutes=vps_data.expires_minutes,
        tags=vps_data.tags,
    )
    db.add(vps)
    db.commit()
    db.refresh(vps)

    config = VPSConfig(
        cpu=cpu,
        ram=ram,
        storage=storage,
        os_image=os_image,
        hostname=vps_data.hostname,
        ssh_key=vps_data.ssh_key,
        password=vps_data.password,
        additional_ports=[p.model_dump() for p in vps_data.additional_ports],
        bandwidth_limit=vps_data.bandwidth_limit,
    )

    job_id = await enqueue_job(
        JobType.VPS_CREATE,
        user_id=current_user.id,
        vps_id=vps.id,
        payload={"config": config.__dict__, "vps_db_id": vps.id}
    )

    return vps


@router.put("/{vps_id}", response_model=VPSResponse)
async def update_vps(
    vps_id: int,
    vps_update: VPSUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = vps_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "additional_ports" and value is not None:
            setattr(vps, field, [p.model_dump() for p in value])
        else:
            setattr(vps, field, value)

    db.commit()
    db.refresh(vps)
    return vps


@router.post("/{vps_id}/start", response_model=VPSActionResponse)
async def start_vps(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    job_id = await enqueue_job(
        JobType.VPS_START,
        user_id=current_user.id,
        vps_id=vps.id,
        payload={"provider_id": vps.provider_id}
    )

    return VPSActionResponse(success=True, message="Start job queued", job_id=job_id)


@router.post("/{vps_id}/stop", response_model=VPSActionResponse)
async def stop_vps(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    job_id = await enqueue_job(
        JobType.VPS_STOP,
        user_id=current_user.id,
        vps_id=vps.id,
        payload={"provider_id": vps.provider_id}
    )

    return VPSActionResponse(success=True, message="Stop job queued", job_id=job_id)


@router.post("/{vps_id}/restart", response_model=VPSActionResponse)
async def restart_vps(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    job_id = await enqueue_job(
        JobType.VPS_RESTART,
        user_id=current_user.id,
        vps_id=vps.id,
        payload={"provider_id": vps.provider_id}
    )

    return VPSActionResponse(success=True, message="Restart job queued", job_id=job_id)


@router.post("/{vps_id}/rebuild", response_model=VPSActionResponse)
async def rebuild_vps(
    vps_id: int,
    request: VPSRebuildRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    job_id = await enqueue_job(
        JobType.VPS_REBUILD,
        user_id=current_user.id,
        vps_id=vps.id,
        payload={"provider_id": vps.provider_id, "os_image": request.os_image}
    )

    return VPSActionResponse(success=True, message="Rebuild job queued", job_id=job_id)


@router.delete("/{vps_id}", response_model=VPSActionResponse)
async def delete_vps(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    job_id = await enqueue_job(
        JobType.VPS_DELETE,
        user_id=current_user.id,
        vps_id=vps.id,
        payload={"provider_id": vps.provider_id}
    )

    return VPSActionResponse(success=True, message="Delete job queued", job_id=job_id)


@router.post("/{vps_id}/password", response_model=VPSActionResponse)
async def change_vps_password(
    vps_id: int,
    request: VPSPasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    new_password = request.password or None

    provider = get_vps_provider()
    success = await provider.change_password(vps.provider_id, new_password)

    if success and new_password:
        vps.root_password = new_password
        db.commit()

    return VPSActionResponse(success=success, message="Password changed" if success else "Failed to change password")


@router.post("/{vps_id}/ports", response_model=VPSActionResponse)
async def add_vps_port(
    vps_id: int,
    request: VPSPortRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    provider = get_vps_provider()
    success = await provider.add_port(vps.provider_id, request.host_port, request.container_port, request.protocol)

    if success:
        ports = vps.additional_ports or []
        ports.append(request.model_dump())
        vps.additional_ports = ports
        db.commit()

    return VPSActionResponse(success=success, message="Port added" if success else "Failed to add port")


@router.delete("/{vps_id}/ports/{host_port}", response_model=VPSActionResponse)
async def remove_vps_port(
    vps_id: int,
    host_port: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    provider = get_vps_provider()
    success = await provider.remove_port(vps.provider_id, host_port)

    if success:
        ports = vps.additional_ports or []
        ports = [p for p in ports if p.get("host_port") != host_port]
        vps.additional_ports = ports
        db.commit()

    return VPSActionResponse(success=success, message="Port removed" if success else "Failed to remove port")


@router.get("/{vps_id}/metrics", response_model=VPSMetricsResponse)
async def get_vps_metrics(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT]:
        raise HTTPException(status_code=403, detail="Access denied")

    provider = get_vps_provider()
    metrics = await provider.get_vps_metrics(vps.provider_id)

    return VPSMetricsResponse(
        cpu_percent=metrics.cpu_percent,
        memory_percent=metrics.memory_percent,
        disk_percent=metrics.disk_percent,
        network_in_bytes=metrics.network_in_bytes,
        network_out_bytes=metrics.network_out_bytes,
        uptime_seconds=metrics.uptime_seconds,
        timestamp=datetime.utcnow()
    )


@router.get("/{vps_id}/console")
async def get_vps_console(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    provider = get_vps_provider()
    console_info = await provider.open_console(vps.provider_id)

    return console_info


@router.post("/{vps_id}/command")
async def execute_vps_command(
    vps_id: int,
    command: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required for command execution")

    provider = get_vps_provider()
    result = await provider.execute_command(vps.provider_id, command)

    return {
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code
    }