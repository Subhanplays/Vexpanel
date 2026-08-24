from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import json

from app.database.session import get_db
from app.models import VPSInstance, TerminalSession, User, UserRole
from app.schemas import TerminalSessionCreate, TerminalSessionResponse
from app.auth.security import get_current_active_user, get_current_user_ws
from app.providers import get_vps_provider

router = APIRouter(prefix="/terminal", tags=["terminal"])


@router.post("/sessions", response_model=TerminalSessionResponse)
async def create_terminal_session(
    session_data: TerminalSessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vps = db.query(VPSInstance).filter(VPSInstance.id == session_data.vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS not found")

    if vps.owner_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    session = TerminalSession(
        session_id=str(uuid.uuid4()),
        user_id=current_user.id,
        vps_id=vps.id,
        is_admin=current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN],
        status="active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get("/sessions", response_model=list[TerminalSessionResponse])
async def list_terminal_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(TerminalSession).filter(TerminalSession.user_id == current_user.id)
    if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        query = db.query(TerminalSession)
    return query.order_by(TerminalSession.created_at.desc()).all()


@router.delete("/sessions/{session_id}")
async def terminate_terminal_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    session = db.query(TerminalSession).filter(TerminalSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")

    session.status = "terminated"
    session.ended_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Session terminated"}


@router.websocket("/ws/{vps_id}")
async def terminal_websocket(
    websocket: WebSocket,
    vps_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    vps = db.query(VPSInstance).filter(VPSInstance.id == vps_id).first()
    if not vps:
        await websocket.close(code=4004, reason="VPS not found")
        return

    if vps.owner_id != user.id and user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        await websocket.close(code=4003, reason="Access denied")
        return

    session = TerminalSession(
        session_id=str(uuid.uuid4()),
        user_id=user.id,
        vps_id=vps.id,
        is_admin=user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN],
        status="active"
    )
    db.add(session)
    db.commit()

    await websocket.accept()

    provider = get_vps_provider()
    console_info = await provider.open_console(vps.provider_id)

    await websocket.send_json({
        "type": "connected",
        "session_id": session.session_id,
        "console_info": console_info
    })

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "input":
                await websocket.send_json({
                    "type": "output",
                    "data": f"Echo: {message.get('data', '')}"
                })
            elif message.get("type") == "resize":
                pass

    except WebSocketDisconnect:
        session.status = "disconnected"
        session.ended_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        session.status = "error"
        session.ended_at = datetime.utcnow()
        db.commit()
        await websocket.close(code=4000, reason=str(e))