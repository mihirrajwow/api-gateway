import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    """Helper: register user, login, return bearer token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Secret123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient):
    token = await _register_and_login(client, "keys1@example.com")
    response = await client.post(
        "/api/v1/api-keys",
        json={"name": "My Key", "rate_limit": 200, "rate_limit_window": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Key"
    assert data["rate_limit"] == 200
    assert data["key"].startswith("gw_")


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient):
    token = await _register_and_login(client, "keys2@example.com")
    for i in range(3):
        await client.post(
            "/api/v1/api-keys",
            json={"name": f"Key {i}"},
            headers={"Authorization": f"Bearer {token}"},
        )

    response = await client.get(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_update_api_key(client: AsyncClient):
    token = await _register_and_login(client, "keys3@example.com")
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Old Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    key_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/api-keys/{key_id}",
        json={"name": "New Name", "rate_limit": 500},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["rate_limit"] == 500


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient):
    token = await _register_and_login(client, "keys4@example.com")
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "To Revoke"},
        headers={"Authorization": f"Bearer {token}"},
    )
    key_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_resp.status_code == 204

    # Key should be gone from listing
    list_resp = await client.get(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    active_ids = [k["id"] for k in list_resp.json() if k["is_active"]]
    assert key_id not in active_ids


@pytest.mark.asyncio
async def test_create_key_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/api-keys", json={"name": "Anon"})
    assert response.status_code == 403
