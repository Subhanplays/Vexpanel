import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "VexPanel"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vexpanel.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    VPS_PROVIDER: str = os.getenv("VPS_PROVIDER", "custom")

    TRYCLOUDFLARE_ENABLED: bool = True
    PINGGY_ENABLED: bool = True
    PINGGY_TOKEN: Optional[str] = os.getenv("PINGGY_TOKEN")

    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASS: Optional[str] = os.getenv("SMTP_PASS")
    SMTP_FROM: Optional[str] = os.getenv("SMTP_FROM")

    MAX_VPS_PER_USER: int = int(os.getenv("MAX_VPS_PER_USER", "3"))
    DEFAULT_OS_IMAGE: str = os.getenv("DEFAULT_OS_IMAGE", "ubuntu:22.04")
    DOCKER_NETWORK: str = os.getenv("DOCKER_NETWORK", "vexpanel_network")
    VPS_HOSTNAME_PREFIX: str = os.getenv("VPS_HOSTNAME_PREFIX", "vex-")

    RDP_DOCKER_IMAGE: str = os.getenv("RDP_DOCKER_IMAGE", "akarita/docker-ubuntu-desktop")
    RDP_INTERNAL_PORT: int = int(os.getenv("RDP_INTERNAL_PORT", "6080"))
    RDP_CONTAINER_PREFIX: str = os.getenv("RDP_CONTAINER_PREFIX", "vexpanel-rdp-")

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()