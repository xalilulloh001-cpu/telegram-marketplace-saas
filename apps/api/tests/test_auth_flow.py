"""End-to-end authentication: customer, seller, tenant isolation, admin, sessions."""
import pytest

from app.core.security import hash_password
from app.models.enums import ShopMemberRole
from app.models.identity import PlatformAdmin, User
from app.models.tenancy import Shop, ShopMember
from tests.test_telegram_auth import build_init_data

pytestmark = pytest.mark.asyncio


async def _seed_shop(db, slug: str, telegram_id: int, role=ShopMemberRole.OWNER):
    user = User(telegram_id=telegram_id)
    shop = Shop(name=slug.title(), slug=slug, order_prefix=slug[0].upper())
    db.add_all([user, shop])
    await db.commit()
    db.add(ShopMember(shop_id=shop.id, user_id=user.id, role=role))
    await db.commit()
    return user, shop


# --- Customer -------------------------------------------------------------

async def test_customer_login_creates_global_identity(client) -> None:
    response = await client.post(
        "/api/v1/auth/telegram", json={"init_data": build_init_data(telegram_id=1001)}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["telegram_id"] == 1001
    assert body["access_token"]


async def test_customer_login_rejects_invalid_signature(client) -> None:
    bad = build_init_data(telegram_id=1002).replace("hash=", "hash=0")
    response = await client.post("/api/v1/auth/telegram", json={"init_data": bad})
    assert response.status_code == 401


async def test_replayed_init_data_is_rejected(client) -> None:
    """Same payload twice: the second attempt must fail even though the signature is valid."""
    init_data = build_init_data(telegram_id=1003)
    first = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    second = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    assert first.status_code == 200
    assert second.status_code == 401


async def test_customer_me_and_logout(client) -> None:
    login = await client.post(
        "/api/v1/auth/telegram", json={"init_data": build_init_data(telegram_id=1004)}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["principal_type"] == "customer"

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204

    after = await client.get("/api/v1/auth/me", headers=headers)
    assert after.status_code == 401


async def test_unauthenticated_access_is_blocked(client) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_invalid_session_token_is_rejected(client) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


# --- Seller ---------------------------------------------------------------

async def test_seller_login_resolves_shop_from_membership(client, db) -> None:
    await _seed_shop(db, "alpha", 2001)
    response = await client.post(
        "/api/v1/auth/telegram/seller", json={"init_data": build_init_data(telegram_id=2001)}
    )
    assert response.status_code == 200
    assert response.json()["shop"]["slug"] == "alpha"


async def test_user_without_membership_cannot_be_seller(client) -> None:
    response = await client.post(
        "/api/v1/auth/telegram/seller", json={"init_data": build_init_data(telegram_id=2002)}
    )
    assert response.status_code == 403


async def test_seller_cannot_claim_another_shop(client, db) -> None:
    """The critical tenant-isolation case: seller A names shop B's id in the request."""
    await _seed_shop(db, "shopa", 2003)
    _, shop_b = await _seed_shop(db, "shopb", 2004)

    response = await client.post(
        "/api/v1/auth/telegram/seller",
        json={"init_data": build_init_data(telegram_id=2003), "shop_id": shop_b.id},
    )
    assert response.status_code == 403


async def test_seller_session_reports_role_permissions(client, db) -> None:
    await _seed_shop(db, "gamma", 2005, role=ShopMemberRole.MANAGER)
    login = await client.post(
        "/api/v1/auth/telegram/seller", json={"init_data": build_init_data(telegram_id=2005)}
    )
    cookies = login.cookies
    me = await client.get("/api/v1/auth/me", cookies=cookies)
    assert me.status_code == 200
    permissions = me.json()["permissions"]
    assert "product:write" in permissions
    assert "shop:member:manage" not in permissions  # manager is not an owner


# --- Super Admin ----------------------------------------------------------

async def test_admin_login_and_me(client, db) -> None:
    db.add(PlatformAdmin(email="boss@example.com", password_hash=hash_password("Str0ngPass!")))
    await db.commit()

    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "boss@example.com", "password": "Str0ngPass!"},
    )
    assert login.status_code == 200
    me = await client.get("/api/v1/admin/auth/me", cookies=login.cookies)
    assert me.status_code == 200
    assert me.json()["email"] == "boss@example.com"


async def test_admin_wrong_password_is_rejected(client, db) -> None:
    db.add(PlatformAdmin(email="boss2@example.com", password_hash=hash_password("Str0ngPass!")))
    await db.commit()
    response = await client.post(
        "/api/v1/admin/auth/login", json={"email": "boss2@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


async def test_admin_unknown_email_is_rejected(client) -> None:
    response = await client.post(
        "/api/v1/admin/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


async def test_admin_endpoint_rejects_customer_session(client) -> None:
    """Realms must not cross: a customer token is not an admin credential."""
    login = await client.post(
        "/api/v1/auth/telegram", json={"init_data": build_init_data(telegram_id=3001)}
    )
    token = login.json()["access_token"]
    response = await client.get(
        "/api/v1/admin/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
