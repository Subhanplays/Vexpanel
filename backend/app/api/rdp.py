from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.session import get_db
from app.models import VPSInstance, RDPInstance, RDPTunnel, RDPStatus, TunnelProvider, TunnelStatus, User, UserRole
from app.schemas import (
    RDPResponse, RDPTunnelCreateRequest, RDPTunnelChangeRequest,
    RDPTunnelResponse, RDPActionResponse
)
from app.auth.security import get_current_active_user
from app.rdp.manager import rdp_manager, RDPState
from app.tunnels.providers import tunnel_manager, TunnelState
from app.jobs.queue import enqueue_job, JobType

router = APIRouter(prefix="/vps/{vps_id}/rdp", tags=["rdp"])


async def get_vps_and_check_access(vps_id: int, current_user: User, db: Session) -> VPSInstance:
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT]:
        raise HTTPException(status_code=403, detail="Access denied")

    return vps


@router.get("", response_model=RDPResponse)
async def get_rdp(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        rdp = RDPInstance(
            vps_id=vps.id,
            owner_id=vps.owner_id,
            status=RDPStatus.NOT_CREATED,
            docker_image="akarita/docker-ubuntu-desktop"
        )
        db.add(rdp)
        db.commit()
        db.refresh(rdp)

    return rdp


@router.post("", response_model=RDPActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_rdp(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if rdp and rdp.status not in [RDPStatus.NOT_CREATED, RDPStatus.ERROR]:
        raise HTTPException(status_code=400, detail="RDP already exists or is being created")

    if not rdp:
        rdp = RDPInstance(
            vps_id=vps.id,
            owner_id=vps.owner_id,
            status=RDPStatus.NOT_CREATED,
            docker_image="akarita/docker-ubuntu-desktop"
        )
        db.add(rdp)
        db.commit()
        db.refresh(rdp)

    job_id = await enqueue_job(
        JobType.RDP_INSTALL,
        user_id=current_user.id,
        vps_id=vps.id,
        rdp_id=rdp.id,
        payload={"provider_id": vps.provider_id, "vps_db_id": vps.id}
    )

    return RDPActionResponse(success=True, message="RDP creation job queued", job_id=job_id)


@router.get("/status", response_model=RDPResponse)
async def get_rdp_status(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        rdp = RDPInstance(
            vps_id=vps.id,
            owner_id=vps.owner_id,
            status=RDPStatus.NOT_CREATED
        )
        db.add(rdp)
        db.commit()
        db.refresh(rdp)

    return rdp


@router.post("/tunnel", response_model=RDPActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_rdp_tunnel(
    vps_id: int,
    request: RDPTunnelCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        raise HTTPException(status_code=404, detail="RDP not found")

    if rdp.status not in [RDPStatus.DOCKER_READY, RDPStatus.SELECTING_TUNNEL, RDPStatus.READY, RDPStatus.ONLINE]:
        raise HTTPException(status_code=400, detail="RDP Docker container not ready")

    job_id = await enqueue_job(
        JobType.TUNNEL_CREATE,
        user_id=current_user.id,
        vps_id=vps.id,
        rdp_id=rdp.id,
        payload={"provider": request.provider.value, "provider_id": vps.provider_id, "internal_port": rdp.internal_port}
    )

    return RDPActionResponse(success=True, message="Tunnel creation job queued", job_id=job_id)


@router.post("/tunnel/change", response_model=RDPActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def change_rdp_tunnel(
    vps_id: int,
    request: RDPTunnelChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        raise HTTPException(status_code=404, detail="RDP not found")

    if rdp.status not in [RDPStatus.READY, RDPStatus.ONLINE]:
        raise HTTPException(status_code=400, detail="RDP not in a state that allows tunnel change")

    job_id = await enqueue_job(
        JobType.TUNNEL_CHANGE,
        user_id=current_user.id,
        vps_id=vps.id,
        rdp_id=rdp.id,
        payload={"new_provider": request.provider.value, "provider_id": vps.provider_id, "internal_port": rdp.internal_port}
    )

    return RDPActionResponse(success=True, message="Tunnel change job queued", job_id=job_id)


@router.post("/tunnel/restart", response_model=RDPActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def restart_rdp_tunnel(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        raise HTTPException(status_code=404, detail="RDP not found")

    if not rdp.tunnel_provider:
        raise HTTPException(status_code=400, detail="No tunnel configured")

    job_id = await enqueue_job(
        JobType.TUNNEL_RESTART,
        user_id=current_user.id,
        vps_id=vps.id,
        rdp_id=rdp.id,
        payload={"provider": rdp.tunnel_provider.value, "provider_id": vps.provider_id, "internal_port": rdp.internal_port}
    )

    return RDPActionResponse(success=True, message="Tunnel restart job queued", job_id=job_id)


@router.post("/restart", response_model=RDPActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def restart_rdp(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        raise HTTPException(status_code=404, detail="RDP not found")

    job_id = await enqueue_job(
        JobType.RDP_RESTART,
        user_id=current_user.id,
        vps_id=vps.id,
        rdp_id=rdp.id,
        payload={"provider_id": vps.provider_id, "vps_db_id": vps.id}
    )

    return RDPActionResponse(success=True, message="RDP restart job queued", job_id=job_id)


@router.post("/stop", response_model=RDPActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def stop_rdp(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        raise HTTPException(status_code=404, detail="RDP not found")

    job_id = await enqueue_job(
        JobType.RDP_STOP,
        user_id=current_user.id,
        vps_id=vps.id,
        rdp_id=rdp.id,
        payload={"provider_id": vps.provider_id}
    )

    return RDPActionResponse(success=True, message="RDP stop job queued", job_id=job_id)


@router.delete("", response_model=RDPActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def delete_rdp(
    vps_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp:
        raise HTTPException(status_code=404, detail="RDP not found")

    job_id = await enqueue_job(
        JobType.RDP_REMOVE,
        user_id=current_user.id,
        vps_id=vps.id,
        rdp_id=rdp.id,
        payload={"provider_id": vps.provider_id}
    )

    return RDPActionResponse(success=True, message="RDP deletion job queued", job_id=job_id)


@router.get("/logs")
async def get_rdp_logs(
    vps_id: int,
    tail: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = await get_vps_and_check_access(vps_id, current_user, db)

    rdp = db.query(RDPInstance).filter(RDPInstance.vps_id == vps.id).first()
    if not rdp or not rdp.docker_container_id:
        raise HTTPException(status_code=404, detail="RDP container not found")

    logs = await rdp_manager.get_container_logs(vps.provider_id, rdp.docker_container_id, tail)
    return {"logs": logs}