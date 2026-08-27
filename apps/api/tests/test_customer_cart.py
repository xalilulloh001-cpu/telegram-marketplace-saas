"""Cart: CRUD, stock validation, price behaviour, totals, tenant isolation."""
import pytest

pytestmark = pytest.mark.asyncio


async def _add(client, ctx, shop_id: int, product_id: int, quantity: int = 1):
    return await client.post(
        f"/api/v1/customer/shops/{shop_id}/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers=ctx["headers"],
    )


async def test_empty_cart(client, customer_factory, public_shop_factory) -> None:
    shop = await public_shop_factory("cempty", 8901)
    ctx = await customer_factory(9901)
    body = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/cart", headers=ctx["headers"])
    ).json()
    assert body["items"] == []
    assert body["subtotal"] == "0"
    assert body["total_items"] == 0


async def test_add_item(client, customer_factory, public_shop_factory, product_factory) -> None:
    shop = await public_shop_factory("cadd", 8902)
    product = await product_factory(shop.id, "Widget", price=100, stock=10)
    ctx = await customer_factory(9902)

    response = await _add(client, ctx, shop.id, product.id, 2)
    assert response.status_code == 201
    body = response.json()
    assert body["total_items"] == 2
    assert body["subtotal"] == "200.00"


async def test_adding_same_product_increases_quantity(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("cdup", 8903)
    product = await product_factory(shop.id, "Widget", price=10, stock=10)
    ctx = await customer_factory(9903)

    await _add(client, ctx, shop.id, product.id, 2)
    body = (await _add(client, ctx, shop.id, product.id, 3)).json()

    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


async def test_quantity_above_stock_rejected(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("cstock", 8904)
    product = await product_factory(shop.id, "Scarce", stock=5)
    ctx = await customer_factory(9904)

    assert (await _add(client, ctx, shop.id, product.id, 6)).status_code == 409


async def test_accumulated_quantity_above_stock_rejected(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    """4 + 4 must not slip past a stock of 5."""
    shop = await public_shop_factory("caccum", 8905)
    product = await product_factory(shop.id, "Scarce", stock=5)
    ctx = await customer_factory(9905)

    await _add(client, ctx, shop.id, product.id, 4)
    assert (await _add(client, ctx, shop.id, product.id, 4)).status_code == 409


async def test_invalid_quantity_rejected(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("cqty", 8906)
    product = await product_factory(shop.id, "Widget", stock=10)
    ctx = await customer_factory(9906)

    assert (await _add(client, ctx, shop.id, product.id, 0)).status_code == 422
    assert (await _add(client, ctx, shop.id, product.id, -1)).status_code == 422


async def test_update_quantity(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("cupd", 8907)
    product = await product_factory(shop.id, "Widget", price=10, stock=10)
    ctx = await customer_factory(9907)
    item_id = (await _add(client, ctx, shop.id, product.id, 2)).json()["items"][0]["item_id"]

    body = (
        await client.patch(
            f"/api/v1/customer/shops/{shop.id}/cart/items/{item_id}",
            json={"quantity": 4},
            headers=ctx["headers"],
        )
    ).json()
    assert body["items"][0]["quantity"] == 4

    too_many = await client.patch(
        f"/api/v1/customer/shops/{shop.id}/cart/items/{item_id}",
        json={"quantity": 11},
        headers=ctx["headers"],
    )
    assert too_many.status_code == 409


async def test_delete_item_and_clear_cart(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("cdel", 8908)
    p1 = await product_factory(shop.id, "One", stock=5)
    p2 = await product_factory(shop.id, "Two", stock=5)
    ctx = await customer_factory(9908)
    item_id = (await _add(client, ctx, shop.id, p1.id)).json()["items"][0]["item_id"]
    await _add(client, ctx, shop.id, p2.id)

    after_delete = await client.delete(
        f"/api/v1/customer/shops/{shop.id}/cart/items/{item_id}", headers=ctx["headers"]
    )
    assert len(after_delete.json()["items"]) == 1

    cleared = await client.delete(
        f"/api/v1/customer/shops/{shop.id}/cart", headers=ctx["headers"]
    )
    assert cleared.json()["items"] == []
    # The cart row survives so checkout always has something to attach to.
    assert cleared.json()["cart_id"] is not None


async def test_price_change_is_reflected(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    """The cart quotes the current price — snapshots belong to orders, not carts."""
    shop = await public_shop_factory("cprice", 8909)
    product = await product_factory(shop.id, "Widget", price=100, stock=10)
    ctx = await customer_factory(9909)
    await _add(client, ctx, shop.id, product.id, 2)

    product.price = 150
    await db.commit()

    body = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/cart", headers=ctx["headers"])
    ).json()
    assert body["subtotal"] == "300.00"


async def test_discount_price_used_for_totals(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("cdisc", 8910)
    product = await product_factory(shop.id, "Sale", price=100, discount_price=80, stock=10)
    ctx = await customer_factory(9910)

    body = (await _add(client, ctx, shop.id, product.id, 2)).json()
    assert body["items"][0]["display_price"] == "80.00"
    assert body["subtotal"] == "160.00"


async def test_unavailable_item_is_flagged_not_removed(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    shop = await public_shop_factory("cunav", 8911)
    product = await product_factory(shop.id, "Widget", price=50, stock=10)
    ctx = await customer_factory(9911)
    await _add(client, ctx, shop.id, product.id, 2)

    product.is_active = False
    await db.commit()

    body = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/cart", headers=ctx["headers"])
    ).json()
    assert len(body["items"]) == 1
    assert body["items"][0]["available"] is False
    # An unavailable line must not inflate the total the customer is quoted.
    assert body["subtotal"] == "0"
    assert body["total_items"] == 0


async def test_cart_response_hides_stock_count(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("chide", 8912)
    product = await product_factory(shop.id, "Widget", stock=42)
    ctx = await customer_factory(9912)
    item = (await _add(client, ctx, shop.id, product.id)).json()["items"][0]
    assert "stock" not in item
    assert item["in_stock"] is True


# --- tenant isolation -----------------------------------------------------

async def test_cross_shop_product_rejected(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop_a = await public_shop_factory("xa", 8920)
    shop_b = await public_shop_factory("xb", 8921)
    b_product = await product_factory(shop_b.id, "B Item", stock=5)
    ctx = await customer_factory(9920)

    assert (await _add(client, ctx, shop_a.id, b_product.id)).status_code == 404


async def test_inactive_product_cannot_be_added(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("xinact", 8922)
    product = await product_factory(shop.id, "Hidden", stock=5, is_active=False)
    ctx = await customer_factory(9922)

    assert (await _add(client, ctx, shop.id, product.id)).status_code == 404


async def test_customers_have_separate_carts(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("xsep", 8923)
    product = await product_factory(shop.id, "Widget", stock=10)
    ctx_a = await customer_factory(9923)
    ctx_b = await customer_factory(9924)

    await _add(client, ctx_a, shop.id, product.id, 2)
    b_cart = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/cart", headers=ctx_b["headers"])
    ).json()
    assert b_cart["items"] == []


async def test_customer_cannot_touch_another_customers_item(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("xitem", 8924)
    product = await product_factory(shop.id, "Widget", stock=10)
    ctx_a = await customer_factory(9925)
    ctx_b = await customer_factory(9926)
    a_item = (await _add(client, ctx_a, shop.id, product.id)).json()["items"][0]["item_id"]

    patched = await client.patch(
        f"/api/v1/customer/shops/{shop.id}/cart/items/{a_item}",
        json={"quantity": 5},
        headers=ctx_b["headers"],
    )
    deleted = await client.delete(
        f"/api/v1/customer/shops/{shop.id}/cart/items/{a_item}", headers=ctx_b["headers"]
    )
    assert patched.status_code == 404
    assert deleted.status_code == 404


async def test_cart_item_from_other_shop_endpoint_is_404(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    """The same customer, but the item belongs to their cart in a different shop."""
    shop_a = await public_shop_factory("xsa", 8925)
    shop_b = await public_shop_factory("xsb", 8926)
    a_product = await product_factory(shop_a.id, "A Item", stock=5)
    ctx = await customer_factory(9927)
    a_item = (await _add(client, ctx, shop_a.id, a_product.id)).json()["items"][0]["item_id"]

    response = await client.delete(
        f"/api/v1/customer/shops/{shop_b.id}/cart/items/{a_item}", headers=ctx["headers"]
    )
    assert response.status_code == 404


async def test_cart_requires_customer_realm(client, seller_factory, public_shop_factory) -> None:
    shop = await public_shop_factory("xrealm", 8927)
    ctx = await seller_factory("sellercart", 8928)
    response = await client.get(
        f"/api/v1/customer/shops/{shop.id}/cart", cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert response.status_code == 403


async def test_cart_requires_authentication(client, public_shop_factory) -> None:
    shop = await public_shop_factory("xanon", 8929)
    assert (await client.get(f"/api/v1/customer/shops/{shop.id}/cart")).status_code == 401
