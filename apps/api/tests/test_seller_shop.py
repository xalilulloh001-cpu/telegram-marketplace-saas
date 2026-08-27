"""Shop settings and member management, including cross-tenant access."""
import pytest

from app.models.enums import ShopMemberRole

pytestmark = pytest.mark.asyncio


async def test_owner_reads_and_updates_shop(client, seller_factory) -> None:
    ctx = await seller_factory("alpha", 5001)
    read = await client.get("/api/v1/seller/shop", cookies=ctx["cookies"], headers=ctx["headers"])
    assert read.status_code == 200
    assert read.json()["slug"] == "alpha"

    updated = await client.patch(
        "/api/v1/seller/shop",
        json={"name": "Alpha Store", "city": "Andijon"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Alpha Store"
    assert updated.json()["city"] == "Andijon"


async def test_manager_cannot_update_shop(client, seller_factory) -> None:
    ctx = await seller_factory("beta", 5002, role=ShopMemberRole.MANAGER)
    response = await client.patch(
        "/api/v1/seller/shop", json={"name": "Nope"}, cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert response.status_code == 403


async def test_shop_update_ignores_unlisted_fields(client, seller_factory) -> None:
    """Mass assignment: slug and status are not in ShopUpdate, so they cannot be set."""
    ctx = await seller_factory("gamma", 5003)
    response = await client.patch(
        "/api/v1/seller/shop",
        json={"name": "Gamma", "slug": "hijacked", "status": "active"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "gamma"


async def test_unauthenticated_shop_access_blocked(client) -> None:
    assert (await client.get("/api/v1/seller/shop")).status_code == 401


# --- members --------------------------------------------------------------

async def test_owner_adds_and_lists_members(client, seller_factory) -> None:
    ctx = await seller_factory("delta", 5004)
    created = await client.post(
        "/api/v1/seller/shop/members",
        json={"telegram_id": 5555, "role": "manager"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    assert created.status_code == 201

    members = await client.get("/api/v1/seller/shop/members", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    assert members.status_code == 200
    assert len(members.json()) == 2


async def test_manager_cannot_manage_members(client, seller_factory) -> None:
    ctx = await seller_factory("epsilon", 5005, role=ShopMemberRole.MANAGER)
    response = await client.post(
        "/api/v1/seller/shop/members",
        json={"telegram_id": 6666, "role": "manager"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    assert response.status_code == 403


async def test_owner_cannot_remove_self(client, seller_factory, db) -> None:
    ctx = await seller_factory("zeta", 5006)
    members = await client.get("/api/v1/seller/shop/members", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    own_id = members.json()[0]["id"]
    response = await client.delete(
        f"/api/v1/seller/shop/members/{own_id}", cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert response.status_code == 409


async def test_cross_tenant_member_access_blocked(client, seller_factory) -> None:
    """Seller A uses a member id belonging to shop B — must look non-existent."""
    ctx_a = await seller_factory("shopa", 5007)
    ctx_b = await seller_factory("shopb", 5008)

    b_members = await client.get("/api/v1/seller/shop/members", 
        cookies=ctx_b["cookies"],
        headers=ctx_b["headers"],
    )
    b_member_id = b_members.json()[0]["id"]

    patched = await client.patch(
        f"/api/v1/seller/shop/members/{b_member_id}",
        json={"role": "manager"},
        cookies=ctx_a["cookies"], headers=ctx_a["headers"],
    )
    deleted = await client.delete(
        f"/api/v1/seller/shop/members/{b_member_id}", 
            cookies=ctx_a["cookies"],
            headers=ctx_a["headers"],
        
    )
    assert patched.status_code == 404
    assert deleted.status_code == 404
