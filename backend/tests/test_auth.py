from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import require_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import create_admin_user


class FakeSession:
    def __init__(self, user: User | None = None) -> None:
        self.user = user
        self.added: User | None = None
        self.rolled_back = False

    def scalar(self, _statement):
        return self.user

    def get(self, _model, _user_id):
        return self.user

    def add(self, user: User) -> None:
        self.added = user
        self.user = user

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, user: User) -> None:
        if user.id is None:
            user.id = uuid4()
        now = datetime.now(timezone.utc)
        user.created_at = now
        user.updated_at = now

    def close(self) -> None:
        return None


def make_user(password: str = "SecurePassword123!", role: UserRole = UserRole.ADMIN, is_active: bool = True) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        name="System Administrator",
        email="admin@example.com",
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def auth_environment(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-for-auth-tests-that-is-long-enough")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_valid_login_returns_token_and_safe_user(auth_environment) -> None:
    fake_db = FakeSession(make_user())
    app.dependency_overrides[get_db] = lambda: fake_db

    response = TestClient(app).post(
        "/auth/login",
        json={"email": " ADMIN@EXAMPLE.COM ", "password": "SecurePassword123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "admin@example.com"
    assert "password_hash" not in body["user"]


@pytest.mark.parametrize(
    "password,is_active",
    [("wrong-password", True), ("SecurePassword123!", False)],
)
def test_invalid_or_inactive_login_is_generic(auth_environment, password: str, is_active: bool) -> None:
    app.dependency_overrides[get_db] = lambda: FakeSession(make_user(is_active=is_active))

    response = TestClient(app).post("/auth/login", json={"email": "admin@example.com", "password": password})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}


def test_me_requires_bearer_token(auth_environment) -> None:
    app.dependency_overrides[get_db] = lambda: FakeSession(make_user())

    response = TestClient(app).get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_returns_current_user_for_valid_token(auth_environment) -> None:
    user = make_user()
    app.dependency_overrides[get_db] = lambda: FakeSession(user)
    login_response = TestClient(app).post(
        "/auth/login", json={"email": user.email, "password": "SecurePassword123!"}
    )

    response = TestClient(app).get(
        "/auth/me", headers={"Authorization": f"Bearer {login_response.json()['access_token']}"}
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_admin_guard_allows_admin_and_rejects_other_roles() -> None:
    assert require_admin(make_user(role=UserRole.ADMIN)).role == UserRole.ADMIN
    with pytest.raises(Exception) as exception:
        require_admin(make_user(role=UserRole.EMPLOYEE))
    assert exception.value.status_code == 403


def test_admin_creation_hashes_password_and_rejects_duplicate() -> None:
    session = FakeSession()
    user = create_admin_user(session, "New Admin", "Admin@Example.com", "SecurePassword123!")

    assert user.role == UserRole.ADMIN
    assert user.is_active
    assert user.email == "admin@example.com"
    assert user.password_hash != "SecurePassword123!"
    assert session.added is user

    with pytest.raises(ValueError, match="already exists"):
        create_admin_user(session, "New Admin", "admin@example.com", "SecurePassword123!")
