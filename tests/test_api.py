import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.session import get_db
from app.models import Base, User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "VexPanel"


def test_setup_super_admin():
    response = client.post("/api/v1/auth/setup", json={
        "email": "admin@example.com",
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_login():
    client.post("/api/v1/auth/setup", json={
        "email": "admin@example.com",
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    })
    
    response = client.post("/api/v1/auth/login", data={
        "username": "admin",
        "password": "securepassword123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_register():
    response = client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "testuser"


def test_vps_plans():
    token = get_admin_token()
    response = client.get("/api/v1/admin/plans", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_operating_systems():
    token = get_admin_token()
    response = client.get("/api/v1/admin/operating-systems", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def get_admin_token():
    client.post("/api/v1/auth/setup", json={
        "email": "admin@example.com",
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    })
    response = client.post("/api/v1/auth/login", data={
        "username": "admin",
        "password": "securepassword123"
    })
    return response.json()["access_token"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])