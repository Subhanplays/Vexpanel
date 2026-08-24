from datetime import datetime, timedelta
from typing import Optional, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models import User, UserRole, APIToken

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    token_type = payload.get("type", "access")
    if token_type != "access":
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    if not user.is_active or user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive or banned"
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_roles(*allowed_roles: UserRole):
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


def require_permissions(*permissions: str):
    def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_permissions = get_user_permissions(current_user.role)
        for perm in permissions:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permission: {perm}"
                )
        return current_user
    return permission_checker


ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: [
        "users.view", "users.manage",
        "vps.view", "vps.create", "vps.manage", "vps.delete",
        "rdp.view", "rdp.manage",
        "terminal.user", "terminal.admin",
        "hosts.view", "hosts.manage",
        "settings.view", "settings.manage",
        "audit.view", "jobs.view", "jobs.manage",
    ],
    UserRole.ADMIN: [
        "users.view", "users.manage",
        "vps.view", "vps.create", "vps.manage", "vps.delete",
        "rdp.view", "rdp.manage",
        "terminal.user", "terminal.admin",
        "hosts.view", "hosts.manage",
        "settings.view", "settings.manage",
        "audit.view", "jobs.view", "jobs.manage",
    ],
    UserRole.SUPPORT: [
        "users.view",
        "vps.view", "vps.manage",
        "rdp.view", "rdp.manage",
        "terminal.user",
        "hosts.view",
        "settings.view",
        "audit.view", "jobs.view",
    ],
    UserRole.READ_ONLY: [
        "users.view",
        "vps.view",
        "rdp.view",
        "hosts.view",
        "settings.view",
        "audit.view", "jobs.view",
    ],
    UserRole.USER: [
        "vps.view", "vps.create", "vps.manage",
        "rdp.view", "rdp.manage",
        "terminal.user",
    ],
}


def get_user_permissions(role: UserRole) -> List[str]:
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(user: User, permission: str) -> bool:
    return permission in get_user_permissions(user.role)


async def get_current_user_ws(token: str, db: Session) -> Optional[User]:
    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active or user.is_banned:
        return None

    return user


def create_api_token_hash(token: str) -> str:
    return get_password_hash(token)


def verify_api_token(token: str, token_hash: str) -> bool:
    return verify_password(token, token_hash)