"""Cart and favorites data access.

Carts are addressed by (customer_id, shop_id) — never by a client-supplied cart id — and
cart items are reachable only through their own cart, so one customer can never touch
another's rows.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Product
from app.models.commerce import Cart, CartItem, Favorite
from app.repositories.base import Page


async def get_cart(db: DbSession, customer_id: int, shop_id: int) -> Cart | None:
    result = await db.execute(
        select(Cart)
        .where(Cart.customer_id == customer_id, Cart.shop_id == shop_id)
        .options(
            selectinload(Cart.items)
            .selectinload(CartItem.product)
            .selectinload(Product.images)
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_cart(db: DbSession, customer_id: int, shop_id: int) -> Cart:
    cart = await get_cart(db, customer_id, shop_id)
    if cart is None:
        cart = Cart(customer_id=customer_id, shop_id=shop_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    return cart


async def get_cart_item(db: DbSession, cart_id: int, item_id: int) -> CartItem | None:
    result = await db.execute(
        select(CartItem)
        .where(CartItem.id == item_id, CartItem.cart_id == cart_id)
        .options(selectinload(CartItem.product).selectinload(Product.images))
    )
    return result.scalar_one_or_none()


async def get_cart_item_by_product(db: DbSession, cart_id: int, product_id: int) -> CartItem | None:
    result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
    )
    return result.scalar_one_or_none()


async def lock_product(db: DbSession, shop_id: int, product_id: int) -> Product | None:
    """Locks the product row for the duration of the transaction so two concurrent
    add-to-cart requests cannot both pass the same stock check."""
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.shop_id == shop_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


# --- favorites ------------------------------------------------------------

async def get_favorite(db: DbSession, customer_id: int, product_id: int) -> Favorite | None:
    """Product and images are eager-loaded: the response needs them, and lazy loading in
    an async session raises rather than silently issuing IO."""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.customer_id == customer_id, Favorite.product_id == product_id)
        .options(selectinload(Favorite.product).selectinload(Product.images))
    )
    return result.scalar_one_or_none()


async def list_favorites(db: DbSession, customer_id: int, page: int, page_size: int) -> Page:
    stmt = (
        select(Favorite)
        .where(Favorite.customer_id == customer_id)
        .options(selectinload(Favorite.product).selectinload(Product.images))
        .order_by(Favorite.created_at.desc(), Favorite.id.desc())
    )
    total = await db.scalar(
        select(func.count()).select_from(Favorite).where(Favorite.customer_id == customer_id)
    ) or 0
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return Page(items=list(result.scalars().all()), page=page, page_size=page_size, total=total)


async def list_favorite_product_ids(db: DbSession, customer_id: int) -> set[int]:
    result = await db.execute(
        select(Favorite.product_id).where(Favorite.customer_id == customer_id)
    )
    return set(result.scalars().all())
