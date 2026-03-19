import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_get_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_me_returns_profile(client: AsyncClient):
    # Register + login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "Secret123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "Secret123"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "api_keys" in data


@pytest.mark.asyncio
async def test_update_me_email(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "update_me@example.com", "password": "Secret123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "update_me@example.com", "password": "Secret123"},
    )
    token = login.json()["access_token"]

    patch = await client.patch(
        "/api/v1/users/me",
        json={"email": "new_email@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch.status_code == 200
    assert patch.json()["email"] == "new_email@example.com"


@pytest.mark.asyncio
async def test_deactivate_account(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "deactivate@example.com", "password": "Secret123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "deactivate@example.com", "password": "Secret123"},
    )
    token = login.json()["access_token"]

    delete = await client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204

    # Subsequent login should fail
    login2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "deactivate@example.com", "password": "Secret123"},
    )
    assert login2.status_code == 401
