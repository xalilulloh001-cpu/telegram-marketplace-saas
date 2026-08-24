"""Customer search, filters, sorting, pagination and realm separation."""
import pytest

pytestmark = pytest.mark.asyncio


# --- search ---------------------------------------------------------------

async def test_search_matches_within_shop(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("srch", 8301)
    await product_factory(shop.id, "iPhone 15 Pro")
    await product_factory(shop.id, "Samsung S24")
    ctx = await customer_factory(9301)

    body = (
        await client.get(
            f"/api/v1/customer/shops/{shop.id}/products?search=iphone", headers=ctx["headers"]
        )
    ).json()
    assert body["total"] == 1


async def test_search_cannot_leak_other_shop(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    """A matching product in another shop must not surface in this shop's search."""
    shop_a = await public_shop_factory("leaka", 8302)
    shop_b = await public_shop_factory("leakb", 8303)
    await product_factory(shop_b.id, "Secret Gadget")
    ctx = await customer_factory(9302)

    body = (
        await client.get(
            f"/api/v1/customer/shops/{shop_a.id}/products?search=Secret", headers=ctx["headers"]
        )
    ).json()
    assert body["total"] == 0


# --- filters --------------------------------------------------------------

async def test_category_filter(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("fcat", 8401)
    category = await product_factory.category(shop.id, "Phones")
    await product_factory(shop.id, "In Category", category_id=category.id)
    await product_factory(shop.id, "Uncategorised")
    ctx = await customer_factory(9401)

    body = (
        await client.get(
            f"/api/v1/customer/shops/{shop.id}/products?category_id={category.id}",
            headers=ctx["headers"],
        )
    ).json()
    assert body["total"] == 1


async def test_price_range_filters(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("fprice", 8402)
    for price in (50, 150, 250):
        await product_factory(shop.id, f"Item {price}", price=price)
    ctx = await customer_factory(9402)

    body = (
        await client.get(
            f"/api/v1/customer/shops/{shop.id}/products?price_min=100&price_max=200",
            headers=ctx["headers"],
        )
    ).json()
    assert body["total"] == 1


async def test_invalid_price_range_rejected(
    client, customer_factory, public_shop_factory
) -> None:
    shop = await public_shop_factory("fbad", 8403)
    ctx = await customer_factory(9403)

    inverted = await client.get(
        f"/api/v1/customer/shops/{shop.id}/products?price_min=200&price_max=100",
        headers=ctx["headers"],
    )
    negative = await client.get(
        f"/api/v1/customer/shops/{shop.id}/products?price_min=-5", headers=ctx["headers"]
    )
    assert inverted.status_code == 422
    assert negative.status_code == 422


async def test_availability_filter(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("fstock", 8404)
    await product_factory(shop.id, "Available", stock=3)
    await product_factory(shop.id, "Sold Out", stock=0)
    ctx = await customer_factory(9404)

    body = (
        await client.get(
            f"/api/v1/customer/shops/{shop.id}/products?in_stock=true", headers=ctx["headers"]
        )
    ).json()
    assert [p["name"] for p in body["items"]] == ["Available"]


# --- sorting --------------------------------------------------------------

@pytest.mark.parametrize("sort", ["newest", "price_asc", "price_desc", "name_asc", "name_desc"])
async def test_allowed_sorts(
    client, customer_factory, public_shop_factory, product_factory, sort: str
) -> None:
    shop = await public_shop_factory(f"s-{sort}", 8500 + len(sort))
    await product_factory(shop.id, "A Item", price=10)
    await product_factory(shop.id, "B Item", price=20)
    ctx = await customer_factory(9500 + len(sort))

    response = await client.get(
        f"/api/v1/customer/shops/{shop.id}/products?sort={sort}", headers=ctx["headers"]
    )
    assert response.status_code == 200


async def test_price_sort_order(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("sortord", 8601)
    await product_factory(shop.id, "Cheap", price=10)
    await product_factory(shop.id, "Pricey", price=90)
    ctx = await customer_factory(9601)

    body = (
        await client.get(
            f"/api/v1/customer/shops/{shop.id}/products?sort=price_desc", headers=ctx["headers"]
        )
    ).json()
    assert [p["name"] for p in body["items"]] == ["Pricey", "Cheap"]


async def test_arbitrary_sort_rejected(
    client, customer_factory, public_shop_factory
) -> None:
    shop = await public_shop_factory("sortbad", 8602)
    ctx = await customer_factory(9602)
    response = await client.get(
        f"/api/v1/customer/shops/{shop.id}/products?sort=price;DROP TABLE products",
        headers=ctx["headers"],
    )
    assert response.status_code == 422


# --- pagination -----------------------------------------------------------

async def test_pagination_defaults_and_bounds(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    shop = await public_shop_factory("pageit", 8701)
    for i in range(5):
        await product_factory(shop.id, f"Item {i}")
    ctx = await customer_factory(9701)

    default = (
        await client.get(f"/api/v1/customer/shops/{shop.id}/products", headers=ctx["headers"])
    ).json()
    assert default["page_size"] == 20
    assert default["total"] == 5

    page2 = (
        await client.get(
            f"/api/v1/customer/shops/{shop.id}/products?page=2&page_size=2",
            headers=ctx["headers"],
        )
    ).json()
    assert page2["page"] == 2
    assert page2["pages"] == 3

    too_big = await client.get(
        f"/api/v1/customer/shops/{shop.id}/products?page_size=500", headers=ctx["headers"]
    )
    assert too_big.status_code == 422


# --- auth / realm separation ----------------------------------------------

async def test_customer_api_requires_authentication(client, public_shop_factory) -> None:
    await public_shop_factory("anon", 8801)
    assert (await client.get("/api/v1/customer/shops")).status_code == 401


async def test_seller_session_cannot_use_customer_api(client, seller_factory) -> None:
    """Realms stay separate: a seller cookie is not a customer credential."""
    ctx = await seller_factory("sellerrealm", 8802)
    response = await client.get("/api/v1/customer/shops", cookies=ctx["cookies"])
    assert response.status_code == 403


async def test_customer_token_cannot_reach_seller_api(client, customer_factory) -> None:
    ctx = await customer_factory(9802)
    response = await client.get("/api/v1/seller/products", headers=ctx["headers"])
    assert response.status_code == 403


async def test_customer_token_cannot_reach_admin_api(client, customer_factory) -> None:
    ctx = await customer_factory(9803)
    response = await client.get("/api/v1/admin/auth/me", headers=ctx["headers"])
    assert response.status_code == 403
