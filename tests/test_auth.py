import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import patch

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.schemas.auth import UserCreate
from app.services.role_seed import ensure_system_roles
from app.services.users import create_user


@pytest_asyncio.fixture
async def auth_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        await ensure_system_roles(session)
        await create_user(
            session,
            UserCreate(email="admin@example.com", password="adminpass1", role="administrator"),
        )
        await create_user(
            session,
            UserCreate(email="common@example.com", password="commonpass1", role="common"),
        )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


async def _login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _login_full(client: AsyncClient, email: str, password: str) -> dict:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_login_success(auth_client: AsyncClient):
    token = await _login(auth_client, "admin@example.com", "adminpass1")
    assert token


@pytest.mark.asyncio
async def test_login_bad_credentials_returns_401(auth_client: AsyncClient):
    response = await auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_users_without_token_returns_401(auth_client: AsyncClient):
    response = await auth_client.get("/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_common_read_ok_list_forbidden(auth_client: AsyncClient):
    token = await _login(auth_client, "common@example.com", "commonpass1")
    headers = {"Authorization": f"Bearer {token}"}

    listed = await auth_client.get("/users", headers=headers)
    assert listed.status_code == 403

    # common has users:read — need an id; admin created users with ids 1 and 2 typically
    me = await auth_client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["id"]

    fetched = await auth_client.get(f"/users/{user_id}", headers=headers)
    assert fetched.status_code == 200

    created = await auth_client.post(
        "/users",
        headers=headers,
        json={"email": "new@example.com", "password": "password12", "role": "common"},
    )
    assert created.status_code == 403


@pytest.mark.asyncio
async def test_administrator_user_crud(auth_client: AsyncClient):
    token = await _login(auth_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    created = await auth_client.post(
        "/users",
        headers=headers,
        json={"email": "newbie@example.com", "password": "password12", "role": "common"},
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    assert created.json()["role"] == "common"

    fetched = await auth_client.get(f"/users/{user_id}", headers=headers)
    assert fetched.status_code == 200

    patched = await auth_client.patch(
        f"/users/{user_id}",
        headers=headers,
        json={"role": "administrator"},
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "administrator"

    deleted = await auth_client.delete(f"/users/{user_id}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_health_and_contact_remain_public(auth_client: AsyncClient):
    health = await auth_client.get("/health")
    assert health.status_code == 200

    with patch("app.api.routes.contact.send_contact_email"):
        contact = await auth_client.post(
            "/contact",
            json={
                "full_name": "Ana García",
                "email": "ana@example.com",
                "service_type": "vehicles_stock",
                "message": "Hola",
                "privacy_policy_acceptance": True,
            },
        )
    assert contact.status_code == 200


@pytest.mark.asyncio
async def test_auth_me(auth_client: AsyncClient):
    token = await _login(auth_client, "admin@example.com", "adminpass1")
    response = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert body["role"] == "administrator"
    scopes = {item["scope"]: set(item["actions"]) for item in body["permissions"]}
    assert "users" in scopes and "roles" in scopes
    assert "list" in scopes["users"] and "delete" in scopes["roles"]


@pytest.mark.asyncio
async def test_auth_me_common_permissions(auth_client: AsyncClient):
    token = await _login(auth_client, "common@example.com", "commonpass1")
    response = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    scopes = {item["scope"]: set(item["actions"]) for item in response.json()["permissions"]}
    assert scopes == {"users": {"read"}}


@pytest.mark.asyncio
async def test_roles_unauthenticated_401(auth_client: AsyncClient):
    response = await auth_client.get("/roles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_common_cannot_access_roles(auth_client: AsyncClient):
    token = await _login(auth_client, "common@example.com", "commonpass1")
    response = await auth_client.get("/roles", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_roles_crud_and_custom_role(auth_client: AsyncClient):
    token = await _login(auth_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    listed = await auth_client.get("/roles", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 2

    created = await auth_client.post(
        "/roles",
        headers=headers,
        json={
            "name": "editor",
            "description": "Can list users",
            "permissions": [{"scope": "users", "actions": ["list", "read"]}],
        },
    )
    assert created.status_code == 201, created.text
    role_id = created.json()["id"]

    user = await auth_client.post(
        "/users",
        headers=headers,
        json={"email": "editor@example.com", "password": "password12", "role": "editor"},
    )
    assert user.status_code == 201

    editor_token = await _login(auth_client, "editor@example.com", "password12")
    editor_headers = {"Authorization": f"Bearer {editor_token}"}
    assert (await auth_client.get("/users", headers=editor_headers)).status_code == 200
    assert (await auth_client.post(
        "/users",
        headers=editor_headers,
        json={"email": "x@example.com", "password": "password12", "role": "common"},
    )).status_code == 403

    deleted_system = await auth_client.delete("/roles/1", headers=headers)
    assert deleted_system.status_code == 400

    blocked = await auth_client.delete(f"/roles/{role_id}", headers=headers)
    assert blocked.status_code == 400

    await auth_client.delete(f"/users/{user.json()['id']}", headers=headers)
    deleted = await auth_client.delete(f"/roles/{role_id}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_login_exposes_must_change_password(auth_client: AsyncClient):
    data = await _login_full(auth_client, "admin@example.com", "adminpass1")
    assert data["must_change_password"] is True

    me = await auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True


@pytest.mark.asyncio
async def test_force_change_password_clears_flag(auth_client: AsyncClient):
    token = await _login(auth_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    changed = await auth_client.post(
        "/auth/force-change-password",
        headers=headers,
        json={"new_password": "newadminpass1"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False

    # Old password no longer works
    assert (
        await auth_client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "adminpass1"},
        )
    ).status_code == 401

    data = await _login_full(auth_client, "admin@example.com", "newadminpass1")
    assert data["must_change_password"] is False

    again = await auth_client.post(
        "/auth/force-change-password",
        headers={"Authorization": f"Bearer {data['access_token']}"},
        json={"new_password": "anotherpass1"},
    )
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_created_user_requires_password_change(auth_client: AsyncClient):
    admin_token = await _login(auth_client, "admin@example.com", "adminpass1")
    # Admin still has must_change_password; clear it first so we can use admin APIs cleanly
    await auth_client.post(
        "/auth/force-change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"new_password": "adminpass1"},
    )
    admin_token = await _login(auth_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {admin_token}"}

    created = await auth_client.post(
        "/users",
        headers=headers,
        json={"email": "fresh@example.com", "password": "temppass12", "role": "common"},
    )
    assert created.status_code == 201
    assert created.json()["must_change_password"] is True

@pytest.mark.asyncio
async def test_logout_requires_authentication(auth_client: AsyncClient):
    response = await auth_client.post("/auth/logout")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_valid_token_returns_204(auth_client: AsyncClient):
    token = await _login(auth_client, "admin@example.com", "adminpass1")
    response = await auth_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_logout_with_garbage_token_returns_401(auth_client: AsyncClient):
    response = await auth_client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
