"""Pagination, filtering, sorting, and image upload rules."""
import io

import pytest

pytestmark = pytest.mark.asyncio

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64


async def _seed_products(client, cookies, count: int, prefix: str = "Item") -> None:
    for i in range(count):
        await client.post(
            "/api/v1/seller/products",
            json={"name": f"{prefix} {i}", "price": f"{10 + i}.00", "stock": i},
            cookies=cookies,
        )


# --- pagination -----------------------------------------------------------

async def test_default_page_size(client, seller_factory) -> None:
    ctx = await seller_factory("pag1", 7001)
    await _seed_products(client, ctx["cookies"], 3)
    body = (await client.get("/api/v1/seller/products", cookies=ctx["cookies"])).json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 3
    assert body["pages"] == 1


async def test_page_boundaries(client, seller_factory) -> None:
    ctx = await seller_factory("pag2", 7002)
    await _seed_products(client, ctx["cookies"], 5)
    page2 = (
        await client.get(
            "/api/v1/seller/products?page=2&page_size=2", cookies=ctx["cookies"]
        )
    ).json()
    assert page2["page"] == 2
    assert page2["pages"] == 3
    assert len(page2["items"]) == 2


async def test_page_size_limits_enforced(client, seller_factory) -> None:
    ctx = await seller_factory("pag3", 7003)
    too_big = await client.get("/api/v1/seller/products?page_size=500", cookies=ctx["cookies"])
    too_small = await client.get("/api/v1/seller/products?page_size=0", cookies=ctx["cookies"])
    bad_page = await client.get("/api/v1/seller/products?page=0", cookies=ctx["cookies"])
    assert too_big.status_code == 422
    assert too_small.status_code == 422
    assert bad_page.status_code == 422


# --- filtering ------------------------------------------------------------

async def test_search_filter(client, seller_factory) -> None:
    ctx = await seller_factory("flt1", 7101)
    await client.post(
        "/api/v1/seller/products",
        json={"name": "iPhone 15 Pro", "price": "1200.00"},
        cookies=ctx["cookies"],
    )
    await client.post(
        "/api/v1/seller/products",
        json={"name": "Samsung S24", "price": "1100.00"},
        cookies=ctx["cookies"],
    )
    found = (
        await client.get("/api/v1/seller/products?search=iphone", cookies=ctx["cookies"])
    ).json()
    assert found["total"] == 1
    assert found["items"][0]["name"] == "iPhone 15 Pro"


async def test_category_filter(client, seller_factory) -> None:
    ctx = await seller_factory("flt2", 7102)
    cid = (
        await client.post(
            "/api/v1/seller/categories", json={"name": "Phones"}, cookies=ctx["cookies"]
        )
    ).json()["id"]
    await client.post(
        "/api/v1/seller/products",
        json={"name": "In category", "price": "10.00", "category_id": cid},
        cookies=ctx["cookies"],
    )
    await client.post(
        "/api/v1/seller/products",
        json={"name": "No category", "price": "10.00"},
        cookies=ctx["cookies"],
    )
    body = (
        await client.get(
            f"/api/v1/seller/products?category_id={cid}", cookies=ctx["cookies"]
        )
    ).json()
    assert body["total"] == 1


async def test_active_filter(client, seller_factory) -> None:
    ctx = await seller_factory("flt3", 7103)
    await client.post(
        "/api/v1/seller/products",
        json={"name": "Hidden", "price": "10.00", "is_active": False},
        cookies=ctx["cookies"],
    )
    await client.post(
        "/api/v1/seller/products",
        json={"name": "Visible", "price": "10.00"},
        cookies=ctx["cookies"],
    )
    active = (
        await client.get("/api/v1/seller/products?is_active=true", cookies=ctx["cookies"])
    ).json()
    assert active["total"] == 1
    assert active["items"][0]["name"] == "Visible"


# --- sorting --------------------------------------------------------------

@pytest.mark.parametrize(
    "sort", ["newest", "oldest", "price_asc", "price_desc", "name_asc", "name_desc"]
)
async def test_allowed_sorts(client, seller_factory, sort: str) -> None:
    ctx = await seller_factory(f"srt-{sort}", 7200 + hash(sort) % 500)
    await _seed_products(client, ctx["cookies"], 3)
    response = await client.get(
        f"/api/v1/seller/products?sort={sort}", cookies=ctx["cookies"]
    )
    assert response.status_code == 200


async def test_price_sorting_order(client, seller_factory) -> None:
    ctx = await seller_factory("srt-order", 7801)
    await _seed_products(client, ctx["cookies"], 3)
    asc = (
        await client.get("/api/v1/seller/products?sort=price_asc", cookies=ctx["cookies"])
    ).json()
    prices = [float(item["price"]) for item in asc["items"]]
    assert prices == sorted(prices)


async def test_arbitrary_sort_rejected(client, seller_factory) -> None:
    """An unknown sort key is refused before it reaches the query builder."""
    ctx = await seller_factory("srt-bad", 7802)
    response = await client.get(
        "/api/v1/seller/products?sort=price;DROP TABLE products", cookies=ctx["cookies"]
    )
    assert response.status_code == 422


# --- images ---------------------------------------------------------------

async def test_image_upload_and_list(client, seller_factory) -> None:
    ctx = await seller_factory("img1", 7901)
    pid = (
        await client.post(
            "/api/v1/seller/products",
            json={"name": "With image", "price": "10.00"},
            cookies=ctx["cookies"],
        )
    ).json()["id"]

    upload = await client.post(
        f"/api/v1/seller/products/{pid}/images",
        files={"file": ("photo.png", io.BytesIO(PNG_BYTES), "image/png")},
        cookies=ctx["cookies"],
    )
    assert upload.status_code == 201
    # The stored URL is generated by our storage layer and is tenant-scoped.
    assert f"shops/{ctx['shop'].id}/products/{pid}/" in upload.json()["url"]

    listed = await client.get(
        f"/api/v1/seller/products/{pid}/images", cookies=ctx["cookies"]
    )
    assert len(listed.json()) == 1


async def test_invalid_file_type_rejected(client, seller_factory) -> None:
    ctx = await seller_factory("img2", 7902)
    pid = (
        await client.post(
            "/api/v1/seller/products",
            json={"name": "Bad upload", "price": "10.00"},
            cookies=ctx["cookies"],
        )
    ).json()["id"]

    response = await client.post(
        f"/api/v1/seller/products/{pid}/images",
        files={"file": ("evil.php", io.BytesIO(b"<?php ?>"), "application/x-php")},
        cookies=ctx["cookies"],
    )
    assert response.status_code == 422


async def test_oversized_file_rejected(client, seller_factory) -> None:
    ctx = await seller_factory("img3", 7903)
    pid = (
        await client.post(
            "/api/v1/seller/products",
            json={"name": "Big upload", "price": "10.00"},
            cookies=ctx["cookies"],
        )
    ).json()["id"]

    oversized = b"0" * (5 * 1024 * 1024 + 10)
    response = await client.post(
        f"/api/v1/seller/products/{pid}/images",
        files={"file": ("big.png", io.BytesIO(oversized), "image/png")},
        cookies=ctx["cookies"],
    )
    assert response.status_code == 422


async def test_cross_tenant_image_access_blocked(client, seller_factory) -> None:
    ctx_a = await seller_factory("img4a", 7904)
    ctx_b = await seller_factory("img4b", 7905)
    b_pid = (
        await client.post(
            "/api/v1/seller/products",
            json={"name": "B product", "price": "10.00"},
            cookies=ctx_b["cookies"],
        )
    ).json()["id"]
    b_img = await client.post(
        f"/api/v1/seller/products/{b_pid}/images",
        files={"file": ("photo.png", io.BytesIO(PNG_BYTES), "image/png")},
        cookies=ctx_b["cookies"],
    )
    b_img_id = b_img.json()["id"]

    assert (
        await client.get(f"/api/v1/seller/products/{b_pid}/images", cookies=ctx_a["cookies"])
    ).status_code == 404
    assert (
        await client.delete(
            f"/api/v1/seller/products/{b_pid}/images/{b_img_id}", cookies=ctx_a["cookies"]
        )
    ).status_code == 404
