"""Categories and products: CRUD, validation, filters, sorting, tenant isolation."""
import pytest

pytestmark = pytest.mark.asyncio


def _csrf(cookies: dict) -> dict:
    """Mirrors the browser: read the readable CSRF cookie and echo it in the header."""
    return {"X-CSRF-Token": cookies.get("mp_csrf", "")}



async def _create_category(client, cookies, name: str, parent_id: int | None = None):
    return await client.post(
        "/api/v1/seller/categories",
        json={"name": name, "parent_id": parent_id},
        cookies=cookies,
        headers=_csrf(cookies),
    )


async def _create_product(client, cookies, **overrides):
    payload = {"name": "iPhone 15", "price": "1000.00", "stock": 5}
    payload.update(overrides)
    return await client.post(
        "/api/v1/seller/products", json=payload, cookies=cookies, headers=_csrf(cookies)
    )


# --- categories -----------------------------------------------------------

async def test_category_crud(client, seller_factory) -> None:
    ctx = await seller_factory("cat1", 6001)
    created = await _create_category(client, ctx["cookies"], "Electronics")
    assert created.status_code == 201
    assert created.json()["slug"] == "electronics"
    cid = created.json()["id"]

    read = await client.get(f"/api/v1/seller/categories/{cid}", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    assert read.status_code == 200

    patched = await client.patch(
        f"/api/v1/seller/categories/{cid}", json={"name": "Gadgets"}, 
            cookies=ctx["cookies"],
            headers=ctx["headers"],
        
    )
    assert patched.status_code == 200
    assert patched.json()["slug"] == "gadgets"

    deleted = await client.delete(f"/api/v1/seller/categories/{cid}", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    assert deleted.status_code == 204


async def test_parent_category(client, seller_factory) -> None:
    ctx = await seller_factory("cat2", 6002)
    parent = await _create_category(client, ctx["cookies"], "Electronics")
    child = await _create_category(
        client, ctx["cookies"], "Phones", parent_id=parent.json()["id"]
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent.json()["id"]


async def test_cross_shop_parent_rejected(client, seller_factory) -> None:
    """Shop A must not attach its category under shop B's category."""
    ctx_a = await seller_factory("cat3a", 6003)
    ctx_b = await seller_factory("cat3b", 6004)
    b_cat = await _create_category(client, ctx_b["cookies"], "Clothing")

    response = await _create_category(
        client, ctx_a["cookies"], "Shoes", parent_id=b_cat.json()["id"]
    )
    assert response.status_code == 404


async def test_cross_tenant_category_access_blocked(client, seller_factory) -> None:
    ctx_a = await seller_factory("cat4a", 6005)
    ctx_b = await seller_factory("cat4b", 6006)
    b_cat_id = (await _create_category(client, ctx_b["cookies"], "Books")).json()["id"]

    assert (
        await client.get(f"/api/v1/seller/categories/{b_cat_id}", 
            cookies=ctx_a["cookies"],
            headers=ctx_a["headers"],
        )
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/seller/categories/{b_cat_id}", json={"name": "X"}, 
                cookies=ctx_a["cookies"],
                headers=ctx_a["headers"],
            
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/seller/categories/{b_cat_id}", 
            cookies=ctx_a["cookies"],
            headers=ctx_a["headers"],
        )
    ).status_code == 404


async def test_category_with_products_cannot_be_deleted(client, seller_factory) -> None:
    ctx = await seller_factory("cat5", 6007)
    cid = (await _create_category(client, ctx["cookies"], "Phones")).json()["id"]
    await _create_product(client, ctx["cookies"], category_id=cid)

    response = await client.delete(f"/api/v1/seller/categories/{cid}", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    assert response.status_code == 409


async def test_category_with_children_cannot_be_deleted(client, seller_factory) -> None:
    ctx = await seller_factory("cat6", 6008)
    parent_id = (await _create_category(client, ctx["cookies"], "Electronics")).json()["id"]
    await _create_category(client, ctx["cookies"], "Phones", parent_id=parent_id)

    response = await client.delete(
        f"/api/v1/seller/categories/{parent_id}", cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert response.status_code == 409


# --- products -------------------------------------------------------------

async def test_product_crud(client, seller_factory) -> None:
    ctx = await seller_factory("prod1", 6101)
    created = await _create_product(client, ctx["cookies"])
    assert created.status_code == 201
    pid = created.json()["id"]
    assert created.json()["slug"] == "iphone-15"

    read = await client.get(f"/api/v1/seller/products/{pid}", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    assert read.status_code == 200

    patched = await client.patch(
        f"/api/v1/seller/products/{pid}", json={"stock": 12}, 
            cookies=ctx["cookies"],
            headers=ctx["headers"],
        
    )
    assert patched.status_code == 200
    assert patched.json()["stock"] == 12

    deleted = await client.delete(f"/api/v1/seller/products/{pid}", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    assert deleted.status_code == 204


async def test_product_shop_id_from_context_not_body(client, seller_factory) -> None:
    """A shop_id in the body is ignored — the tenant context decides ownership."""
    ctx_a = await seller_factory("prod2a", 6102)
    ctx_b = await seller_factory("prod2b", 6103)

    created = await _create_product(
        client, ctx_a["cookies"], shop_id=ctx_b["shop"].id, name="Injected"
    )
    assert created.status_code == 201
    assert created.json()["shop_id"] == ctx_a["shop"].id


async def test_invalid_price_rejected(client, seller_factory) -> None:
    ctx = await seller_factory("prod3", 6104)
    assert (await _create_product(client, ctx["cookies"], price="0")).status_code == 422
    assert (await _create_product(client, ctx["cookies"], price="-5")).status_code == 422


async def test_invalid_discount_rejected(client, seller_factory) -> None:
    ctx = await seller_factory("prod4", 6105)
    response = await _create_product(
        client, ctx["cookies"], price="100.00", discount_price="150.00"
    )
    assert response.status_code == 422


async def test_negative_stock_rejected(client, seller_factory) -> None:
    ctx = await seller_factory("prod5", 6106)
    assert (await _create_product(client, ctx["cookies"], stock=-1)).status_code == 422


async def test_empty_name_rejected(client, seller_factory) -> None:
    ctx = await seller_factory("prod6", 6107)
    assert (await _create_product(client, ctx["cookies"], name="")).status_code == 422


async def test_wrong_shop_category_rejected(client, seller_factory) -> None:
    ctx_a = await seller_factory("prod7a", 6108)
    ctx_b = await seller_factory("prod7b", 6109)
    b_cat_id = (await _create_category(client, ctx_b["cookies"], "Audio")).json()["id"]

    response = await _create_product(client, ctx_a["cookies"], category_id=b_cat_id)
    assert response.status_code == 404


async def test_duplicate_name_gets_unique_slug(client, seller_factory) -> None:
    """Slugs are shop-scoped and de-duplicated server-side rather than erroring."""
    ctx = await seller_factory("prod8", 6110)
    first = await _create_product(client, ctx["cookies"], name="Same Name")
    second = await _create_product(client, ctx["cookies"], name="Same Name")
    assert first.json()["slug"] == "same-name"
    assert second.json()["slug"] == "same-name-2"


async def test_same_slug_allowed_across_shops(client, seller_factory) -> None:
    ctx_a = await seller_factory("prod9a", 6111)
    ctx_b = await seller_factory("prod9b", 6112)
    a = await _create_product(client, ctx_a["cookies"], name="Shared")
    b = await _create_product(client, ctx_b["cookies"], name="Shared")
    assert a.json()["slug"] == b.json()["slug"] == "shared"


async def test_cross_tenant_product_blocked(client, seller_factory) -> None:
    ctx_a = await seller_factory("prod10a", 6113)
    ctx_b = await seller_factory("prod10b", 6114)
    b_pid = (await _create_product(client, ctx_b["cookies"])).json()["id"]

    assert (
        await client.get(f"/api/v1/seller/products/{b_pid}", 
            cookies=ctx_a["cookies"],
            headers=ctx_a["headers"],
        )
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/seller/products/{b_pid}", json={"stock": 1}, 
                cookies=ctx_a["cookies"],
                headers=ctx_a["headers"],
            
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/seller/products/{b_pid}", 
            cookies=ctx_a["cookies"],
            headers=ctx_a["headers"],
        )
    ).status_code == 404


async def test_product_list_is_shop_scoped(client, seller_factory) -> None:
    ctx_a = await seller_factory("prod11a", 6115)
    ctx_b = await seller_factory("prod11b", 6116)
    await _create_product(client, ctx_a["cookies"], name="A item")
    await _create_product(client, ctx_b["cookies"], name="B item")

    listing = await client.get("/api/v1/seller/products", 
        cookies=ctx_a["cookies"],
        headers=ctx_a["headers"],
    )
    names = [item["name"] for item in listing.json()["items"]]
    assert names == ["A item"]
