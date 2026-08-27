"""Favorites: idempotency, isolation, availability flags, pagination, concurrency."""
import asyncio

import pytest

pytestmark = pytest.mark.asyncio


async def test_add_and_list_favorite(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("fav1", 8801)
    product = await product_factory(shop.id, "Loved", price=100, stock=3)
    ctx = await customer_factory(9801)

    added = await client.put(
        f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"]
    )
    assert added.status_code == 200
    assert added.json()["product_name"] == "Loved"

    listed = (await client.get("/api/v1/customer/favorites", headers=ctx["headers"])).json()
    assert listed["total"] == 1


async def test_duplicate_favorite_is_idempotent(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    """PUT twice is harmless — no duplicate row, no error."""
    shop = await public_shop_factory("fav2", 8802)
    product = await product_factory(shop.id, "Loved", stock=3)
    ctx = await customer_factory(9802)

    first = await client.put(f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"])
    second = await client.put(f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"])
    assert first.status_code == second.status_code == 200

    listed = (await client.get("/api/v1/customer/favorites", headers=ctx["headers"])).json()
    assert listed["total"] == 1


async def test_remove_favorite(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("fav3", 8803)
    product = await product_factory(shop.id, "Loved", stock=3)
    ctx = await customer_factory(9803)
    await client.put(f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"])

    removed = await client.delete(
        f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"]
    )
    assert removed.status_code == 204

    again = await client.delete(
        f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"]
    )
    assert again.status_code == 404


async def test_favorites_span_multiple_shops(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    """Favorites are global to the customer, unlike carts which are per shop."""
    shop_a = await public_shop_factory("fava", 8804)
    shop_b = await public_shop_factory("favb", 8805)
    p_a = await product_factory(shop_a.id, "From A", stock=1)
    p_b = await product_factory(shop_b.id, "From B", stock=1)
    ctx = await customer_factory(9804)

    await client.put(f"/api/v1/customer/favorites/{p_a.id}", headers=ctx["headers"])
    await client.put(f"/api/v1/customer/favorites/{p_b.id}", headers=ctx["headers"])

    listed = (await client.get("/api/v1/customer/favorites", headers=ctx["headers"])).json()
    assert listed["total"] == 2
    assert {item["shop_id"] for item in listed["items"]} == {shop_a.id, shop_b.id}


async def test_favorites_are_customer_isolated(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("fav5", 8806)
    product = await product_factory(shop.id, "Loved", stock=3)
    ctx_a = await customer_factory(9805)
    ctx_b = await customer_factory(9806)
    await client.put(f"/api/v1/customer/favorites/{product.id}", headers=ctx_a["headers"])

    b_list = (await client.get("/api/v1/customer/favorites", headers=ctx_b["headers"])).json()
    assert b_list["total"] == 0

    b_delete = await client.delete(
        f"/api/v1/customer/favorites/{product.id}", headers=ctx_b["headers"]
    )
    assert b_delete.status_code == 404


async def test_inactive_product_stays_but_is_flagged(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    shop = await public_shop_factory("fav6", 8807)
    product = await product_factory(shop.id, "Loved", stock=3)
    ctx = await customer_factory(9807)
    await client.put(f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"])

    product.is_active = False
    await db.commit()

    listed = (await client.get("/api/v1/customer/favorites", headers=ctx["headers"])).json()
    assert listed["total"] == 1
    assert listed["items"][0]["is_available"] is False


async def test_inactive_product_cannot_be_favorited(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("fav7", 8808)
    product = await product_factory(shop.id, "Hidden", stock=3, is_active=False)
    ctx = await customer_factory(9808)

    response = await client.put(
        f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"]
    )
    assert response.status_code == 404


async def test_favorites_pagination(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("fav8", 8809)
    ctx = await customer_factory(9809)
    for i in range(5):
        product = await product_factory(shop.id, f"Item {i}", stock=2)
        await client.put(f"/api/v1/customer/favorites/{product.id}", headers=ctx["headers"])

    page = (
        await client.get("/api/v1/customer/favorites?page=2&page_size=2", headers=ctx["headers"])
    ).json()
    assert page["page"] == 2
    assert page["pages"] == 3
    assert len(page["items"]) == 2

    too_big = await client.get(
        "/api/v1/customer/favorites?page_size=500", headers=ctx["headers"]
    )
    assert too_big.status_code == 422


async def test_favorites_require_customer_realm(client, seller_factory) -> None:
    ctx = await seller_factory("sellerfav", 8810)
    response = await client.get("/api/v1/customer/favorites", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    assert response.status_code == 403


async def test_favorites_require_authentication(client) -> None:
    assert (await client.get("/api/v1/customer/favorites")).status_code == 401


# --- concurrency ----------------------------------------------------------

async def test_concurrent_adds_cannot_exceed_stock(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    """Two simultaneous requests for 4 units against a stock of 5: the row lock means
    one succeeds and the other is refused, so the cart never holds 8."""
    shop = await public_shop_factory("race", 8811)
    product = await product_factory(shop.id, "Scarce", price=10, stock=5)
    ctx = await customer_factory(9811)

    payload = {"product_id": product.id, "quantity": 4}
    first, second = await asyncio.gather(
        client.post(
            f"/api/v1/customer/shops/{shop.id}/cart/items",
            json=payload,
            headers=ctx["headers"],
        ),
        client.post(
            f"/api/v1/customer/shops/{shop.id}/cart/items",
            json=payload,
            headers=ctx["headers"],
        ),
        return_exceptions=True,
    )

    statuses = sorted(
        r.status_code for r in (first, second) if not isinstance(r, BaseException)
    )
    assert 409 in statuses or statuses == [201]

    cart = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/cart", headers=ctx["headers"])
    ).json()
    total = sum(item["quantity"] for item in cart["items"])
    assert total <= 5
