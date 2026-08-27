"""Integration test fixtures backed by a real PostgreSQL database."""
import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TEST-TOKEN")
# Secure cookies are not transmitted over the plain-http test transport.
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("COOKIE_SAMESITE", "lax")
os.environ.setdefault("CSRF_SECRET", "test-csrf-secret")

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace_test",
)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seller_factory(client, db):
    """Creates a shop with an owner and returns an authenticated client context."""
    from app.models.enums import ShopMemberRole
    from app.models.identity import User
    from app.models.tenancy import Shop, ShopMember
    from tests.test_telegram_auth import build_init_data

    async def make(slug: str, telegram_id: int, role: ShopMemberRole = ShopMemberRole.OWNER):
        user = User(telegram_id=telegram_id)
        shop = Shop(name=slug.title(), slug=slug, order_prefix=slug[0].upper())
        db.add_all([user, shop])
        await db.commit()
        db.add(ShopMember(shop_id=shop.id, user_id=user.id, role=role))
        await db.commit()
        login = await client.post(
            "/api/v1/auth/telegram/seller",
            json={"init_data": build_init_data(telegram_id=telegram_id)},
        )
        assert login.status_code == 200, login.text
        cookies = dict(login.cookies)
        # Browser clients echo the readable CSRF cookie back in a header; tests do the same.
        headers = {"X-CSRF-Token": cookies.get("mp_csrf", "")}
        return {"shop": shop, "user": user, "cookies": cookies, "headers": headers}

    return make


@pytest_asyncio.fixture
async def customer_factory(client):
    """Logs in a customer and returns bearer auth headers."""
    from tests.test_telegram_auth import build_init_data

    async def make(telegram_id: int):
        login = await client.post(
            "/api/v1/auth/telegram", json={"init_data": build_init_data(telegram_id=telegram_id)}
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        return {"headers": {"Authorization": f"Bearer {token}"}, "token": token}

    return make


@pytest_asyncio.fixture
async def public_shop_factory(db):
    """Creates a shop in a given status with an owner (no login)."""
    from app.models.enums import ShopMemberRole, ShopStatus
    from app.models.identity import User
    from app.models.tenancy import Shop, ShopMember

    async def make(slug: str, telegram_id: int, status: ShopStatus = ShopStatus.ACTIVE):
        user = User(telegram_id=telegram_id)
        shop = Shop(name=slug.title(), slug=slug, order_prefix=slug[0].upper(), status=status)
        db.add_all([user, shop])
        await db.commit()
        db.add(ShopMember(shop_id=shop.id, user_id=user.id, role=ShopMemberRole.OWNER))
        await db.commit()
        return shop

    return make


@pytest_asyncio.fixture
async def product_factory(db):
    from app.models.catalog import Category, Product

    async def make(shop_id: int, name: str, **kwargs):
        product = Product(
            shop_id=shop_id,
            name=name,
            slug=name.lower().replace(" ", "-"),
            price=kwargs.pop("price", 100),
            stock=kwargs.pop("stock", 5),
            is_active=kwargs.pop("is_active", True),
            **kwargs,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    async def make_category(shop_id: int, name: str, is_active: bool = True, parent_id=None):
        category = Category(
            shop_id=shop_id,
            name=name,
            slug=name.lower().replace(" ", "-"),
            is_active=is_active,
            parent_id=parent_id,
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    make.category = make_category
    return make
