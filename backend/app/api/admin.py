from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.models import User, UserRole, VPSInstance, RDPInstance, VPSPlan, OperatingSystem, Host, AuditLog, Job, JobStatus, Setting
from app.schemas import (
    UserResponse, UserCreate, UserUpdate,
    VPSPlanCreate, VPSPlanUpdate, VPSPlanResponse,
    OperatingSystemCreate, OperatingSystemResponse,
    HostCreate, HostUpdate, HostResponse,
    AuditLogResponse, JobResponse,
    SettingResponse, SettingUpdate
)
from app.auth.security import get_current_active_user, require_roles, require_permissions

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
async def admin_dashboard(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    total_vps = db.query(VPSInstance).count()
    online_vps = db.query(VPSInstance).filter(VPSInstance.status == "running").count()
    total_rdp = db.query(RDPInstance).count()
    online_rdp = db.query(RDPInstance).filter(RDPInstance.status == "online").count()
    total_hosts = db.query(Host).filter(Host.is_active == True).count()
    running_jobs = db.query(Job).filter(Job.status == JobStatus.RUNNING).count()

    return {
        "total_users": total_users,
        "total_vps": total_vps,
        "online_vps": online_vps,
        "total_rdp": total_rdp,
        "online_rdp": online_rdp,
        "total_hosts": total_hosts,
        "running_jobs": running_jobs,
    }


@router.get("/users", response_model=List[UserResponse])
async def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if search:
        query = query.filter(User.username.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if user_data.email and db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    from app.auth.security import get_password_hash
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
async def admin_get_user(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "password" and value:
            from app.auth.security import get_password_hash
            user.hashed_password = get_password_hash(value)
        else:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"success": True, "message": "User deleted"}


@router.post("/users/{user_id}/ban")
async def admin_ban_user(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_banned = True
    db.commit()
    return {"success": True, "message": "User banned"}


@router.post("/users/{user_id}/unban")
async def admin_unban_user(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_banned = False
    db.commit()
    return {"success": True, "message": "User unbanned"}


@router.get("/vps", response_model=List[dict])
async def admin_list_all_vps(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db)
):
    query = db.query(VPSInstance)
    if status:
        query = query.filter(VPSInstance.status == status)

    total = query.count()
    vps_list = query.order_by(VPSInstance.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return [{
        "id": v.id,
        "vps_id": v.vps_id,
        "owner": v.owner.username if v.owner else "Unknown",
        "status": v.status.value,
        "cpu": v.cpu,
        "ram": v.ram,
        "storage": v.storage,
        "ipv4": v.ipv4,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    } for v in vps_list]


@router.get("/vps/{vps_id}", response_model=dict)
async def admin_get_vps(
    vps_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    return {
        "id": vps.id,
        "vps_id": vps.vps_id,
        "provider_id": vps.provider_id,
        "token": vps.token,
        "owner": vps.owner.username if vps.owner else "Unknown",
        "owner_id": vps.owner_id,
        "plan_id": vps.plan_id,
        "cpu": vps.cpu,
        "ram": vps.ram,
        "storage": vps.storage,
        "hostname": vps.hostname,
        "ipv4": vps.ipv4,
        "ipv6": vps.ipv6,
        "status": vps.status.value,
        "provider_status": vps.provider_status,
        "ssh_port": vps.ssh_port,
        "additional_ports": vps.additional_ports,
        "container_id": vps.container_id,
        "image_id": vps.image_id,
        "created_at": vps.created_at.isoformat() if vps.created_at else None,
        "expires_at": vps.expires_at.isoformat() if vps.expires_at else None,
    }


@router.post("/vps/{vps_id}/suspend")
async def admin_suspend_vps(
    vps_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    from app.providers import get_vps_provider
    provider = get_vps_provider()
    await provider.stop_vps(vps.provider_id)

    vps.status = "suspended"
    db.commit()
    return {"success": True, "message": "VPS suspended"}


@router.post("/vps/{vps_id}/unsuspend")
async def admin_unsuspend_vps(
    vps_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    from app.providers import get_vps_provider
    provider = get_vps_provider()
    await provider.start_vps(vps.provider_id)

    vps.status = "running"
    db.commit()
    return {"success": True, "message": "VPS unsuspended"}


@router.get("/rdp", response_model=List[dict])
async def admin_list_rdp(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db)
):
    query = db.query(RDPInstance).join(VPSInstance)
    if status:
        query = query.filter(RDPInstance.status == status)

    total = query.count()
    rdp_list = query.order_by(RDPInstance.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return [{
        "id": r.id,
        "vps_id": r.vps.vps_id if r.vps else "Unknown",
        "vps_db_id": r.vps_id,
        "owner": r.owner.username if r.owner else "Unknown",
        "status": r.status.value,
        "docker_container_id": r.docker_container_id,
        "tunnel_provider": r.tunnel_provider.value if r.tunnel_provider else None,
        "tunnel_status": r.tunnel_status.value,
        "tunnel_url": r.tunnel_url,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rdp_list]


@router.get("/rdp/{rdp_id}", response_model=dict)
async def admin_get_rdp(
    rdp_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db)
):
    rdp = db.query(RDPInstance).filter(RDPInstance.id == rdp_id).first()
    if not rdp:
        raise HTTPException(status_code=404, detail="RDP not found")

    return {
        "id": rdp.id,
        "vps": rdp.vps.vps_id if rdp.vps else None,
        "owner": rdp.owner.username if rdp.owner else None,
        "status": rdp.status.value,
        "docker_container_id": rdp.docker_container_id,
        "docker_container_name": rdp.docker_container_name,
        "docker_image": rdp.docker_image,
        "internal_port": rdp.internal_port,
        "tunnel_provider": rdp.tunnel_provider.value if rdp.tunnel_provider else None,
        "tunnel_status": rdp.tunnel_status.value,
        "tunnel_url": rdp.tunnel_url,
        "last_error": rdp.last_error,
        "created_at": rdp.created_at.isoformat() if rdp.created_at else None,
        "updated_at": rdp.updated_at.isoformat() if rdp.updated_at else None,
    }


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def admin_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT)),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return logs


@router.get("/jobs", response_model=List[JobResponse])
async def admin_list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = None,
    job_type: Optional[str] = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    if job_type:
        query = query.filter(Job.job_type == job_type)

    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jobs


@router.get("/settings", response_model=List[SettingResponse])
async def admin_list_settings(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    return db.query(Setting).all()


@router.put("/settings/{key}", response_model=SettingResponse)
async def admin_update_setting(
    key: str,
    setting_update: SettingUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        setting = Setting(key=key, value=setting_update.value)
        db.add(setting)
    else:
        setting.value = setting_update.value
    db.commit()
    db.refresh(setting)
    return setting


@router.get("/plans", response_model=List[VPSPlanResponse])
async def admin_list_plans(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    return db.query(VPSPlan).order_by(VPSPlan.name).all()


@router.post("/plans", response_model=VPSPlanResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_plan(
    plan_data: VPSPlanCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    if db.query(VPSPlan).filter(VPSPlan.name == plan_data.name).first():
        raise HTTPException(status_code=400, detail="Plan name already exists")

    plan = VPSPlan(**plan_data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/plans/{plan_id}", response_model=VPSPlanResponse)
async def admin_update_plan(
    plan_id: int,
    plan_update: VPSPlanUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    plan = db.query(VPSPlan).filter(VPSPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = plan_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/plans/{plan_id}")
async def admin_delete_plan(
    plan_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    plan = db.query(VPSPlan).filter(VPSPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    db.delete(plan)
    db.commit()
    return {"success": True, "message": "Plan deleted"}


@router.get("/operating-systems", response_model=List[OperatingSystemResponse])
async def admin_list_operating_systems(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    return db.query(OperatingSystem).order_by(OperatingSystem.sort_order).all()


@router.post("/operating-systems", response_model=OperatingSystemResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_operating_system(
    os_data: OperatingSystemCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    if db.query(OperatingSystem).filter(OperatingSystem.name == os_data.name, OperatingSystem.version == os_data.version).first():
        raise HTTPException(status_code=400, detail="OS with this name and version already exists")

    os_obj = OperatingSystem(**os_data.model_dump())
    db.add(os_obj)
    db.commit()
    db.refresh(os_obj)
    return os_obj


@router.get("/hosts", response_model=List[HostResponse])
async def admin_list_hosts(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    return db.query(Host).all()


@router.post("/hosts", response_model=HostResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_host(
    host_data: HostCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    if db.query(Host).filter(Host.name == host_data.name).first():
        raise HTTPException(status_code=400, detail="Host name already exists")

    host = Host(**host_data.model_dump())
    db.add(host)
    db.commit()
    db.refresh(host)
    return host


@router.put("/hosts/{host_id}", response_model=HostResponse)
async def admin_update_host(
    host_id: int,
    host_update: HostUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db)
):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    update_data = host_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(host, field, value)

    db.commit()
    db.refresh(host)
    return host