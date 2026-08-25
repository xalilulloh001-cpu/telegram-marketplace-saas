"""Checkout: snapshots, stock, transactions, idempotency, concurrency."""
import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.catalog import Product
from app.models.orders import Order

pytestmark = pytest.mark.asyncio


async def _add_to_cart(client, ctx, shop_id, product_id, quantity=1):
    return await client.post(
        f"/api/v1/customer/shops/{shop_id}/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers=ctx["headers"],
    )


async def _checkout(client, ctx, shop_id, **body):
    return await client.post(
        f"/api/v1/customer/shops/{shop_id}/checkout", json=body, headers=ctx["headers"]
    )


async def test_checkout_creates_order_and_clears_cart(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("co1", 10001)
    product = await product_factory(shop.id, "Widget", price=100, stock=10)
    ctx = await customer_factory(11001)
    await _add_to_cart(client, ctx, shop.id, product.id, 2)

    response = await _checkout(client, ctx, shop.id)
    assert response.status_code == 201
    body = response.json()
    assert body["subtotal"] == "200.00"
    assert body["total"] == "200.00"
    assert body["status"] == "pending"
    assert len(body["items"]) == 1

    cart = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/cart", headers=ctx["headers"])
    ).json()
    assert cart["items"] == []


async def test_order_number_is_shop_scoped(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop_a = await public_shop_factory("alpha", 10002)
    shop_b = await public_shop_factory("bravo", 10003)
    pa = await product_factory(shop_a.id, "A", stock=5)
    pb = await product_factory(shop_b.id, "B", stock=5)
    ctx = await customer_factory(11002)

    await _add_to_cart(client, ctx, shop_a.id, pa.id)
    order_a = (await _checkout(client, ctx, shop_a.id)).json()
    await _add_to_cart(client, ctx, shop_b.id, pb.id)
    order_b = (await _checkout(client, ctx, shop_b.id)).json()

    assert order_a["order_number"].startswith("A-")
    assert order_b["order_number"].startswith("B-")
    # Both shops start their own sequence, so the numeric part repeats across shops.
    assert order_a["order_number"].split("-")[1] == order_b["order_number"].split("-")[1]


async def test_stock_is_decremented(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    shop = await public_shop_factory("co3", 10004)
    product = await product_factory(shop.id, "Widget", stock=10)
    ctx = await customer_factory(11003)
    await _add_to_cart(client, ctx, shop.id, product.id, 4)
    await _checkout(client, ctx, shop.id)

    refreshed = await db.scalar(select(Product).where(Product.id == product.id))
    await db.refresh(refreshed)
    assert refreshed.stock == 6


async def test_price_snapshot_survives_price_change(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    """The seller raising the price later must not rewrite an existing order."""
    shop = await public_shop_factory("co4", 10005)
    product = await product_factory(shop.id, "Widget", price=100, stock=10)
    ctx = await customer_factory(11004)
    await _add_to_cart(client, ctx, shop.id, product.id, 2)
    order = (await _checkout(client, ctx, shop.id)).json()

    product.price = Decimal("500")
    await db.commit()

    fetched = (
        await client.get(f"/api/v1/customer/orders/{order['id']}", headers=ctx["headers"])
    ).json()
    assert fetched["subtotal"] == "200.00"
    assert fetched["items"][0]["unit_price"] == "100.00"


async def test_checkout_uses_current_price_not_cart_price(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    """Price changes between add-to-cart and checkout are honoured by the server."""
    shop = await public_shop_factory("co5", 10006)
    product = await product_factory(shop.id, "Widget", price=100, stock=10)
    ctx = await customer_factory(11005)
    await _add_to_cart(client, ctx, shop.id, product.id, 1)

    product.price = Decimal("120")
    await db.commit()

    order = (await _checkout(client, ctx, shop.id)).json()
    assert order["subtotal"] == "120.00"


async def test_discount_price_snapshot(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("co6", 10007)
    product = await product_factory(shop.id, "Sale", price=100, discount_price=80, stock=5)
    ctx = await customer_factory(11006)
    await _add_to_cart(client, ctx, shop.id, product.id, 2)

    order = (await _checkout(client, ctx, shop.id)).json()
    assert order["items"][0]["unit_price"] == "80.00"
    assert order["items"][0]["list_price"] == "100.00"
    assert order["subtotal"] == "160.00"


async def test_empty_cart_checkout_rejected(
    client, customer_factory, public_shop_factory
) -> None:
    shop = await public_shop_factory("co7", 10008)
    ctx = await customer_factory(11007)
    assert (await _checkout(client, ctx, shop.id)).status_code == 409


async def test_inactive_product_blocks_checkout(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    shop = await public_shop_factory("co8", 10009)
    product = await product_factory(shop.id, "Widget", stock=10)
    ctx = await customer_factory(11008)
    await _add_to_cart(client, ctx, shop.id, product.id, 2)

    product.is_active = False
    await db.commit()

    response = await _checkout(client, ctx, shop.id)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["items"][0]["reason"] == "unavailable"

    # The cart is left intact so the customer can decide what to do.
    cart = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/cart", headers=ctx["headers"])
    ).json()
    assert len(cart["items"]) == 1


async def test_insufficient_stock_blocks_checkout(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    shop = await public_shop_factory("co9", 10010)
    product = await product_factory(shop.id, "Widget", stock=10)
    ctx = await customer_factory(11009)
    await _add_to_cart(client, ctx, shop.id, product.id, 8)

    product.stock = 3
    await db.commit()

    response = await _checkout(client, ctx, shop.id)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["items"][0]["reason"] == "insufficient_stock"
    assert detail["items"][0]["available_stock"] == 3


async def test_multi_item_checkout_is_all_or_nothing(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    """One bad line rolls the whole order back — no partial order, no stock movement."""
    shop = await public_shop_factory("co10", 10011)
    good = await product_factory(shop.id, "Good", stock=10)
    bad = await product_factory(shop.id, "Bad", stock=10)
    ctx = await customer_factory(11010)
    await _add_to_cart(client, ctx, shop.id, good.id, 2)
    await _add_to_cart(client, ctx, shop.id, bad.id, 5)

    bad.stock = 1
    await db.commit()

    assert (await _checkout(client, ctx, shop.id)).status_code == 409

    orders = (await client.get("/api/v1/customer/orders", headers=ctx["headers"])).json()
    assert orders["total"] == 0
    await db.refresh(good)
    assert good.stock == 10  # untouched


async def test_multi_item_checkout_creates_one_order(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("co11", 10012)
    p1 = await product_factory(shop.id, "One", price=10, stock=10)
    p2 = await product_factory(shop.id, "Two", price=20, stock=10)
    p3 = await product_factory(shop.id, "Three", price=30, stock=10)
    ctx = await customer_factory(11011)
    await _add_to_cart(client, ctx, shop.id, p1.id, 2)
    await _add_to_cart(client, ctx, shop.id, p2.id, 1)
    await _add_to_cart(client, ctx, shop.id, p3.id, 4)

    order = (await _checkout(client, ctx, shop.id)).json()
    assert len(order["items"]) == 3
    assert order["subtotal"] == "160.00"  # 20 + 20 + 120


async def test_checkout_only_clears_that_shops_cart(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop_a = await public_shop_factory("co12a", 10013)
    shop_b = await public_shop_factory("co12b", 10014)
    pa = await product_factory(shop_a.id, "A", stock=5)
    pb = await product_factory(shop_b.id, "B", stock=5)
    ctx = await customer_factory(11012)
    await _add_to_cart(client, ctx, shop_a.id, pa.id, 2)
    await _add_to_cart(client, ctx, shop_b.id, pb.id, 3)

    await _checkout(client, ctx, shop_a.id)

    cart_b = (
        await client.get(f"/api/v1/customer/shops/{shop_b.id}/cart", headers=ctx["headers"])
    ).json()
    assert cart_b["items"][0]["quantity"] == 3


async def test_client_supplied_totals_are_ignored(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("co13", 10015)
    product = await product_factory(shop.id, "Widget", price=100, stock=5)
    ctx = await customer_factory(11013)
    await _add_to_cart(client, ctx, shop.id, product.id, 1)

    order = (
        await _checkout(client, ctx, shop.id, subtotal="1", total="1", price="1")
    ).json()
    assert order["subtotal"] == "100.00"


# --- address & contact ----------------------------------------------------

async def test_address_snapshot_survives_address_change(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    from app.models.identity import Address, Customer, User

    shop = await public_shop_factory("co14", 10016)
    product = await product_factory(shop.id, "Widget", stock=5)
    ctx = await customer_factory(11014)

    user = await db.scalar(select(User).where(User.telegram_id == 11014))
    customer = await db.scalar(select(Customer).where(Customer.user_id == user.id))
    address = Address(customer_id=customer.id, full_address="Andijon, 1-uy", phone="+998901234567")
    db.add(address)
    await db.commit()

    await _add_to_cart(client, ctx, shop.id, product.id)
    order = (await _checkout(client, ctx, shop.id, address_id=address.id)).json()
    assert order["address_snapshot"] == "Andijon, 1-uy"

    address.full_address = "Toshkent, 2-uy"
    await db.commit()

    fetched = (
        await client.get(f"/api/v1/customer/orders/{order['id']}", headers=ctx["headers"])
    ).json()
    assert fetched["address_snapshot"] == "Andijon, 1-uy"


async def test_other_customers_address_is_404(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    from app.models.identity import Address, Customer, User

    shop = await public_shop_factory("co15", 10017)
    product = await product_factory(shop.id, "Widget", stock=5)
    ctx_a = await customer_factory(11015)
    await customer_factory(11016)  # customer B, whose address A will try to use

    user_b = await db.scalar(select(User).where(User.telegram_id == 11016))
    customer_b = await db.scalar(select(Customer).where(Customer.user_id == user_b.id))
    address_b = Address(customer_id=customer_b.id, full_address="B manzili")
    db.add(address_b)
    await db.commit()

    await _add_to_cart(client, ctx_a, shop.id, product.id)
    response = await _checkout(client, ctx_a, shop.id, address_id=address_b.id)
    assert response.status_code == 404


# --- idempotency & concurrency --------------------------------------------

async def test_idempotency_key_prevents_double_order(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("co16", 10018)
    product = await product_factory(shop.id, "Widget", stock=10)
    ctx = await customer_factory(11017)
    await _add_to_cart(client, ctx, shop.id, product.id, 2)

    first = await _checkout(client, ctx, shop.id, idempotency_key="abc-123")
    second = await _checkout(client, ctx, shop.id, idempotency_key="abc-123")

    assert first.json()["id"] == second.json()["id"]
    orders = (await client.get("/api/v1/customer/orders", headers=ctx["headers"])).json()
    assert orders["total"] == 1


async def test_concurrent_checkout_cannot_oversell(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    """Two customers, 4 units each, stock 5 — one wins, stock never goes negative."""
    shop = await public_shop_factory("race2", 10019)
    product = await product_factory(shop.id, "Scarce", price=10, stock=5)
    ctx_a = await customer_factory(11018)
    ctx_b = await customer_factory(11019)
    await _add_to_cart(client, ctx_a, shop.id, product.id, 4)
    await _add_to_cart(client, ctx_b, shop.id, product.id, 4)

    results = await asyncio.gather(
        _checkout(client, ctx_a, shop.id),
        _checkout(client, ctx_b, shop.id),
        return_exceptions=True,
    )
    statuses = sorted(
        r.status_code for r in results if not isinstance(r, BaseException)
    )
    assert 201 in statuses

    await db.refresh(product)
    assert product.stock >= 0
    assert product.stock == 1


async def test_concurrent_checkouts_get_distinct_order_numbers(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    shop = await public_shop_factory("race3", 10020)
    p1 = await product_factory(shop.id, "One", stock=50)
    p2 = await product_factory(shop.id, "Two", stock=50)
    ctx_a = await customer_factory(11020)
    ctx_b = await customer_factory(11021)
    await _add_to_cart(client, ctx_a, shop.id, p1.id, 1)
    await _add_to_cart(client, ctx_b, shop.id, p2.id, 1)
    assert ctx_a["headers"] != ctx_b["headers"]

    await asyncio.gather(
        _checkout(client, ctx_a, shop.id),
        _checkout(client, ctx_b, shop.id),
        return_exceptions=True,
    )

    numbers = (
        await db.execute(select(Order.order_number).where(Order.shop_id == shop.id))
    ).scalars().all()
    assert len(numbers) == len(set(numbers))
