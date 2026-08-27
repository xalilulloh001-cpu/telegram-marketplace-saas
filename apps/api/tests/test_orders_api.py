"""Customer and seller order APIs: isolation, status machine, RBAC."""
import pytest

from app.models.enums import ShopMemberRole

pytestmark = pytest.mark.asyncio


async def _place_order(client, ctx, shop_id, product_id, quantity=1, **body):
    await client.post(
        f"/api/v1/customer/shops/{shop_id}/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers=ctx["headers"],
    )
    response = await client.post(
        f"/api/v1/customer/shops/{shop_id}/checkout", json=body, headers=ctx["headers"]
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- customer orders ------------------------------------------------------

async def test_customer_lists_own_orders(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("oa1", 12001)
    product = await product_factory(shop.id, "Widget", stock=20)
    ctx = await customer_factory(13001)
    await _place_order(client, ctx, shop.id, product.id)
    await _place_order(client, ctx, shop.id, product.id)

    body = (await client.get("/api/v1/customer/orders", headers=ctx["headers"])).json()
    assert body["total"] == 2
    assert body["items"][0]["shop_name"] == shop.name


async def test_customer_order_pagination(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("oa2", 12002)
    product = await product_factory(shop.id, "Widget", stock=20)
    ctx = await customer_factory(13002)
    for _ in range(3):
        await _place_order(client, ctx, shop.id, product.id)

    page = (
        await client.get("/api/v1/customer/orders?page=2&page_size=2", headers=ctx["headers"])
    ).json()
    assert page["page"] == 2
    assert page["pages"] == 2
    too_big = await client.get(
        "/api/v1/customer/orders?page_size=500", headers=ctx["headers"]
    )
    assert too_big.status_code == 422


async def test_customer_cannot_read_another_customers_order(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("oa3", 12003)
    product = await product_factory(shop.id, "Widget", stock=20)
    ctx_a = await customer_factory(13003)
    ctx_b = await customer_factory(13004)
    order = await _place_order(client, ctx_a, shop.id, product.id)

    response = await client.get(
        f"/api/v1/customer/orders/{order['id']}", headers=ctx_b["headers"]
    )
    assert response.status_code == 404


async def test_customer_can_cancel_pending_order(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    shop = await public_shop_factory("oa4", 12004)
    product = await product_factory(shop.id, "Widget", stock=10)
    ctx = await customer_factory(13005)
    order = await _place_order(client, ctx, shop.id, product.id, quantity=3)

    await db.refresh(product)
    assert product.stock == 7

    cancelled = await client.post(
        f"/api/v1/customer/orders/{order['id']}/cancel", headers=ctx["headers"]
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    # Cancelling returns the reserved units to the shelf.
    await db.refresh(product)
    assert product.stock == 10


async def test_customer_cannot_cancel_confirmed_order(
    client, customer_factory, product_factory, seller_factory, db
) -> None:
    """Once the seller confirms, cancelling becomes the seller's decision."""
    from app.models.enums import ShopStatus

    shop_ctx = await seller_factory("oa5", 12005)
    shop_id = shop_ctx["shop"].id
    shop_ctx["shop"].status = ShopStatus.ACTIVE
    await db.commit()
    product = await product_factory(shop_id, "Widget", stock=10)
    ctx = await customer_factory(13006)
    order = await _place_order(client, ctx, shop_id, product.id)

    await client.patch(
        f"/api/v1/seller/orders/{order['id']}/status",
        json={"status": "confirmed"},
        cookies=shop_ctx["cookies"], headers=shop_ctx["headers"],
    )
    response = await client.post(
        f"/api/v1/customer/orders/{order['id']}/cancel", headers=ctx["headers"]
    )
    assert response.status_code == 409


# --- seller orders --------------------------------------------------------

async def test_seller_sees_only_own_shop_orders(
    client, customer_factory, seller_factory, product_factory, db
) -> None:
    from app.models.enums import ShopStatus

    ctx_a = await seller_factory("sa1", 12010)
    ctx_b = await seller_factory("sb1", 12011)
    ctx_a["shop"].status = ShopStatus.ACTIVE
    ctx_b["shop"].status = ShopStatus.ACTIVE
    await db.commit()

    pa = await product_factory(ctx_a["shop"].id, "A item", stock=10)
    pb = await product_factory(ctx_b["shop"].id, "B item", stock=10)
    customer = await customer_factory(13010)
    order_a = await _place_order(client, customer, ctx_a["shop"].id, pa.id)
    await _place_order(client, customer, ctx_b["shop"].id, pb.id)

    listing = (await client.get("/api/v1/seller/orders", 
        cookies=ctx_a["cookies"],
        headers=ctx_a["headers"],
    )).json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == order_a["id"]


async def test_seller_cannot_read_other_shop_order(
    client, customer_factory, seller_factory, product_factory, db
) -> None:
    from app.models.enums import ShopStatus

    ctx_a = await seller_factory("sa2", 12012)
    ctx_b = await seller_factory("sb2", 12013)
    ctx_b["shop"].status = ShopStatus.ACTIVE
    await db.commit()

    pb = await product_factory(ctx_b["shop"].id, "B item", stock=10)
    customer = await customer_factory(13011)
    order_b = await _place_order(client, customer, ctx_b["shop"].id, pb.id)

    read = await client.get(
        f"/api/v1/seller/orders/{order_b['id']}", cookies=ctx_a["cookies"], headers=ctx_a["headers"]
    )
    patched = await client.patch(
        f"/api/v1/seller/orders/{order_b['id']}/status",
        json={"status": "confirmed"},
        cookies=ctx_a["cookies"], headers=ctx_a["headers"],
    )
    assert read.status_code == 404
    assert patched.status_code == 404


async def test_seller_status_filter(
    client, customer_factory, seller_factory, product_factory, db
) -> None:
    from app.models.enums import ShopStatus

    ctx = await seller_factory("sf1", 12014)
    ctx["shop"].status = ShopStatus.ACTIVE
    await db.commit()
    product = await product_factory(ctx["shop"].id, "Widget", stock=20)
    customer = await customer_factory(13012)
    first = await _place_order(client, customer, ctx["shop"].id, product.id)
    await _place_order(client, customer, ctx["shop"].id, product.id)

    await client.patch(
        f"/api/v1/seller/orders/{first['id']}/status",
        json={"status": "confirmed"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    confirmed = (
        await client.get("/api/v1/seller/orders?status=confirmed", 
            cookies=ctx["cookies"],
            headers=ctx["headers"],
        )
    ).json()
    assert confirmed["total"] == 1


# --- status machine -------------------------------------------------------

async def test_valid_status_progression(
    client, customer_factory, seller_factory, product_factory, db
) -> None:
    from app.models.enums import ShopStatus

    ctx = await seller_factory("st1", 12015)
    ctx["shop"].status = ShopStatus.ACTIVE
    await db.commit()
    product = await product_factory(ctx["shop"].id, "Widget", stock=10)
    customer = await customer_factory(13013)
    order = await _place_order(client, customer, ctx["shop"].id, product.id)

    for target in ("confirmed", "processing", "shipped", "delivered"):
        response = await client.patch(
            f"/api/v1/seller/orders/{order['id']}/status",
            json={"status": target},
            cookies=ctx["cookies"], headers=ctx["headers"],
        )
        assert response.status_code == 200, target
        assert response.json()["status"] == target


async def test_invalid_transitions_rejected(
    client, customer_factory, seller_factory, product_factory, db
) -> None:
    """Skipping ahead, reviving a delivered order, or cancelling one — all refused."""
    from app.models.enums import ShopStatus

    ctx = await seller_factory("st2", 12016)
    ctx["shop"].status = ShopStatus.ACTIVE
    await db.commit()
    product = await product_factory(ctx["shop"].id, "Widget", stock=10)
    customer = await customer_factory(13014)
    order = await _place_order(client, customer, ctx["shop"].id, product.id)

    skipped = await client.patch(
        f"/api/v1/seller/orders/{order['id']}/status",
        json={"status": "delivered"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    assert skipped.status_code == 409

    for target in ("confirmed", "processing", "shipped", "delivered"):
        await client.patch(
            f"/api/v1/seller/orders/{order['id']}/status",
            json={"status": target},
            cookies=ctx["cookies"], headers=ctx["headers"],
        )

    for target in ("cancelled", "pending"):
        response = await client.patch(
            f"/api/v1/seller/orders/{order['id']}/status",
            json={"status": target},
            cookies=ctx["cookies"], headers=ctx["headers"],
        )
        assert response.status_code == 409, target


async def test_unknown_status_rejected(
    client, customer_factory, seller_factory, product_factory, db
) -> None:
    from app.models.enums import ShopStatus

    ctx = await seller_factory("st3", 12017)
    ctx["shop"].status = ShopStatus.ACTIVE
    await db.commit()
    product = await product_factory(ctx["shop"].id, "Widget", stock=10)
    customer = await customer_factory(13015)
    order = await _place_order(client, customer, ctx["shop"].id, product.id)

    response = await client.patch(
        f"/api/v1/seller/orders/{order['id']}/status",
        json={"status": "refunded"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    assert response.status_code == 422


async def test_seller_cancellation_restores_stock(
    client, customer_factory, seller_factory, product_factory, db
) -> None:
    from app.models.enums import ShopStatus

    ctx = await seller_factory("st4", 12018)
    ctx["shop"].status = ShopStatus.ACTIVE
    await db.commit()
    product = await product_factory(ctx["shop"].id, "Widget", stock=10)
    customer = await customer_factory(13016)
    order = await _place_order(client, customer, ctx["shop"].id, product.id, quantity=4)

    await db.refresh(product)
    assert product.stock == 6

    await client.patch(
        f"/api/v1/seller/orders/{order['id']}/status",
        json={"status": "cancelled"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    await db.refresh(product)
    assert product.stock == 10


# --- realms ---------------------------------------------------------------

async def test_customer_cannot_use_seller_order_api(client, customer_factory) -> None:
    ctx = await customer_factory(13020)
    assert (
        await client.get("/api/v1/seller/orders", headers=ctx["headers"])
    ).status_code == 403


async def test_seller_cannot_use_customer_order_api(client, seller_factory) -> None:
    ctx = await seller_factory("realm1", 12020)
    assert (
        await client.get("/api/v1/customer/orders", cookies=ctx["cookies"], headers=ctx["headers"])
    ).status_code == 403


async def test_manager_can_view_but_permissions_are_enforced(
    client, customer_factory, seller_factory, product_factory, db
) -> None:
    """MANAGER holds ORDER_VIEW and ORDER_UPDATE, so the board is usable for fulfilment."""
    from app.models.enums import ShopStatus

    ctx = await seller_factory("mgr1", 12021, role=ShopMemberRole.MANAGER)
    ctx["shop"].status = ShopStatus.ACTIVE
    await db.commit()
    product = await product_factory(ctx["shop"].id, "Widget", stock=10)
    customer = await customer_factory(13021)
    order = await _place_order(client, customer, ctx["shop"].id, product.id)

    listing = await client.get("/api/v1/seller/orders", 
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    updated = await client.patch(
        f"/api/v1/seller/orders/{order['id']}/status",
        json={"status": "confirmed"},
        cookies=ctx["cookies"], headers=ctx["headers"],
    )
    assert listing.status_code == 200
    assert updated.status_code == 200


async def test_order_api_requires_authentication(client) -> None:
    assert (await client.get("/api/v1/customer/orders")).status_code == 401
    assert (await client.get("/api/v1/seller/orders")).status_code == 401
