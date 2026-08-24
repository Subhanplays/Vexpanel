from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models import User, UserRole
from app.schemas import UserCreate, UserResponse, Token, SetupRequest, SetupResponse
from app.auth.security import (
    verify_password, get_password_hash, create_access_token, get_current_user,
    get_current_active_user, require_roles
)

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/setup", response_model=SetupResponse)
@router.post("/setup/", response_model=SetupResponse, include_in_schema=False)
async def setup_super_admin(request: SetupRequest, db: Session = Depends(get_db)):
    existing_admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
    if existing_admin:
        raise HTTPException(status_code=400, detail="Super admin already exists")

    if request.password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user = User(
        username="admin",
        email=request.email,
        hashed_password=get_password_hash(request.password),
        role=UserRole.SUPER_ADMIN,
        is_active=True
    )
    db.add(user)
    db.commit()

    return SetupResponse(success=True, message="Super admin created successfully")


@router.post("/login", response_model=Token)
@router.post("/login/", response_model=Token, include_in_schema=False)
async def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active or user.is_banned:
        raise HTTPException(status_code=403, detail="User is inactive or banned")

    user.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id), "type": "access"})
    return Token(access_token=access_token, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/register", response_model=UserResponse)
@router.post("/register/", response_model=UserResponse, include_in_schema=False)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    if user_data.email and db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

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


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if "email" in user_update and user_update["email"]:
        existing = db.query(User).filter(User.email == user_update["email"], User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = user_update["email"]

    if "theme" in user_update:
        current_user.theme = user_update["theme"]

    if "password" in user_update and user_update["password"]:
        current_user.hashed_password = get_password_hash(user_update["password"])

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/logout")
async def logout():
    return {"success": True, "message": "Logged out successfully"}