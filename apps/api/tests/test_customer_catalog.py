"""Customer catalog: visibility rules, isolation, filters, sorting, pagination, auth."""
import pytest

from app.models.enums import ShopStatus

pytestmark = pytest.mark.asyncio


# --- shop discovery -------------------------------------------------------

async def test_active_shop_is_visible(client, customer_factory, public_shop_factory) -> None:
    await public_shop_factory("visible", 8001)
    ctx = await customer_factory(9001)
    body = (await client.get("/api/v1/customer/shops", headers=ctx["headers"])).json()
    assert [s["slug"] for s in body["items"]] == ["visible"]


async def test_blocked_and_trial_shops_are_hidden(
    client, customer_factory, public_shop_factory
) -> None:
    await public_shop_factory("blocked", 8002, status=ShopStatus.BLOCKED)
    await public_shop_factory("trialshop", 8003, status=ShopStatus.TRIAL)
    ctx = await customer_factory(9002)
    body = (await client.get("/api/v1/customer/shops", headers=ctx["headers"])).json()
    assert body["total"] == 0


async def test_hidden_shop_detail_is_404(client, customer_factory, public_shop_factory) -> None:
    shop = await public_shop_factory("hidden", 8004, status=ShopStatus.BLOCKED)
    ctx = await customer_factory(9003)
    response = await client.get(
        f"/api/v1/customer/shops/{shop.id}", headers=ctx["headers"]
    )
    assert response.status_code == 404


async def test_shop_detail_hides_internal_fields(
    client, customer_factory, public_shop_factory
) -> None:
    """status, plan_id and order_seq are seller/internal state and must not leak."""
    shop = await public_shop_factory("clean", 8005)
    ctx = await customer_factory(9004)
    body = (
        await client.get(f"/api/v1/customer/shops/{shop.id}", headers=ctx["headers"])
    ).json()
    for leaked in ("status", "plan_id", "order_seq", "order_prefix"):
        assert leaked not in body


async def test_shop_search_and_sort(client, customer_factory, public_shop_factory) -> None:
    await public_shop_factory("alpha", 8006)
    await public_shop_factory("beta", 8007)
    ctx = await customer_factory(9005)

    found = (
        await client.get("/api/v1/customer/shops?search=alph", headers=ctx["headers"])
    ).json()
    assert found["total"] == 1

    sorted_shops = (
        await client.get("/api/v1/customer/shops?sort=name_asc", headers=ctx["headers"])
    ).json()
    assert [s["name"] for s in sorted_shops["items"]] == ["Alpha", "Beta"]


# --- products -------------------------------------------------------------

async def test_active_product_visible_inactive_hidden(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("prods", 8101)
    await product_factory(shop.id, "Visible Item")
    await product_factory(shop.id, "Hidden Item", is_active=False)
    ctx = await customer_factory(9101)

    body = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/products", headers=ctx["headers"])
    ).json()
    assert [p["name"] for p in body["items"]] == ["Visible Item"]


async def test_inactive_product_detail_is_404(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("prods2", 8102)
    product = await product_factory(shop.id, "Hidden", is_active=False)
    ctx = await customer_factory(9102)
    response = await client.get(
        f"/api/v1/customer/shops/{shop.id}/products/{product.id}", headers=ctx["headers"]
    )
    assert response.status_code == 404


async def test_product_from_another_shop_is_404(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop_a = await public_shop_factory("shopa5", 8103)
    shop_b = await public_shop_factory("shopb5", 8104)
    b_product = await product_factory(shop_b.id, "B Item")
    ctx = await customer_factory(9103)

    response = await client.get(
        f"/api/v1/customer/shops/{shop_a.id}/products/{b_product.id}", headers=ctx["headers"]
    )
    assert response.status_code == 404


async def test_product_response_hides_stock_count(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    """Availability is a boolean; the exact stock number stays internal."""
    shop = await public_shop_factory("prods3", 8105)
    await product_factory(shop.id, "Item", stock=7)
    ctx = await customer_factory(9104)
    item = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/products", headers=ctx["headers"])
    ).json()["items"][0]
    assert "stock" not in item
    assert item["in_stock"] is True


async def test_display_price_uses_discount(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("prods4", 8106)
    await product_factory(shop.id, "Sale Item", price=100, discount_price=80)
    ctx = await customer_factory(9105)
    item = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/products", headers=ctx["headers"])
    ).json()["items"][0]
    assert item["display_price"] == "80.00"


async def test_product_detail_includes_images_and_category(
    client, customer_factory, public_shop_factory, product_factory, db
) -> None:
    from app.models.catalog import ProductImage

    shop = await public_shop_factory("detail", 8107)
    category = await product_factory.category(shop.id, "Phones")
    product = await product_factory(shop.id, "Phone X", category_id=category.id)
    db.add(ProductImage(product_id=product.id, shop_id=shop.id, url="https://x/1.png"))
    await db.commit()
    ctx = await customer_factory(9106)

    body = (
        await client.get(
            f"/api/v1/customer/shops/{shop.id}/products/{product.id}", headers=ctx["headers"]
        )
    ).json()
    assert body["category"]["name"] == "Phones"
    assert len(body["images"]) == 1


# --- categories -----------------------------------------------------------

async def test_categories_are_shop_scoped_and_active_only(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop_a = await public_shop_factory("cata", 8201)
    shop_b = await public_shop_factory("catb", 8202)
    await product_factory.category(shop_a.id, "Electronics")
    await product_factory.category(shop_a.id, "Archived", is_active=False)
    await product_factory.category(shop_b.id, "Clothing")
    ctx = await customer_factory(9201)

    body = (
        await client.get(f"/api/v1/customer/shops/{shop_a.id}/categories", headers=ctx["headers"])
    ).json()
    assert [c["name"] for c in body] == ["Electronics"]


async def test_category_hierarchy_is_returned(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("cathier", 8203)
    parent = await product_factory.category(shop.id, "Electronics")
    await product_factory.category(shop.id, "Phones", parent_id=parent.id)
    ctx = await customer_factory(9202)

    body = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/categories", headers=ctx["headers"])
    ).json()
    child = next(c for c in body if c["name"] == "Phones")
    assert child["parent_id"] == parent.id


async def test_cross_shop_category_filter_is_404(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop_a = await public_shop_factory("cfa", 8204)
    shop_b = await public_shop_factory("cfb", 8205)
    b_category = await product_factory.category(shop_b.id, "Clothing")
    ctx = await customer_factory(9203)

    response = await client.get(
        f"/api/v1/customer/shops/{shop_a.id}/products?category_id={b_category.id}",
        headers=ctx["headers"],
    )
    assert response.status_code == 404
