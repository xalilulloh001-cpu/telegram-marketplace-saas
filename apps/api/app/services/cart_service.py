"""Cart and favorites business rules.

Two decisions worth stating explicitly:

* **Cart shows the current price.** Line totals are recomputed from `products.price` on
  every read, so a seller's price change is reflected immediately. The immutable
  `price_snapshot` belongs to orders (Phase 7) — a cart is a wish, an order is a contract.
* **Unavailable items stay in the cart.** When a product goes inactive or out of stock the
  row is kept and flagged, so the customer sees *why* the total changed instead of finding
  the item silently gone. Checkout will block on those flags later.
"""
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.models.catalog import Product
from app.models.commerce import Cart, CartItem, Favorite
from app.repositories import cart as repo
from app.schemas.cart import CartItemResponse, CartResponse, FavoriteResponse

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _display_price(product: Product) -> Decimal:
    return product.discount_price if product.discount_price is not None else product.price


def _first_image(product: Product) -> str | None:
    images = sorted(product.images, key=lambda i: (i.sort_order, i.id))
    return images[0].url if images else None


def _to_item_response(item: CartItem) -> CartItemResponse:
    product = item.product
    unit = _display_price(product)
    return CartItemResponse(
        item_id=item.id,
        product_id=product.id,
        product_name=product.name,
        image_url=_first_image(product),
        quantity=item.qty,
        unit_price=product.price,
        display_price=unit,
        line_total=unit * item.qty,
        in_stock=product.stock > 0,
        available=product.is_active and product.stock > 0,
    )


def to_cart_response(cart: Cart | None, shop_id: int) -> CartResponse:
    if cart is None:
        return CartResponse(
            cart_id=None, shop_id=shop_id, items=[], subtotal=Decimal("0"), total_items=0
        )

    items = [_to_item_response(i) for i in sorted(cart.items, key=lambda i: i.id)]
    # Only sellable lines count toward the subtotal, so an unavailable item never inflates it.
    subtotal = sum((i.line_total for i in items if i.available), Decimal("0"))
    total_items = sum(i.quantity for i in items if i.available)
    return CartResponse(
        cart_id=cart.id,
        shop_id=shop_id,
        items=items,
        subtotal=subtotal,
        total_items=total_items,
    )


async def _sellable_product(db: DbSession, shop_id: int, product_id: int) -> Product:
    """Locks and validates the product. A product from another shop, or an inactive one,
    is reported as simply not existing."""
    product = await repo.lock_product(db, shop_id, product_id)
    if product is None or not product.is_active:
        raise _NOT_FOUND
    return product


async def get_cart(db: DbSession, customer_id: int, shop_id: int) -> CartResponse:
    return to_cart_response(await repo.get_cart(db, customer_id, shop_id), shop_id)


async def add_item(
    db: DbSession, customer_id: int, shop_id: int, product_id: int, quantity: int
) -> CartResponse:
    product = await _sellable_product(db, shop_id, product_id)
    cart = await repo.get_or_create_cart(db, customer_id, shop_id)
    existing = await repo.get_cart_item_by_product(db, cart.id, product.id)

    # Re-adding the same product raises the quantity instead of creating a second line.
    requested = (existing.qty if existing else 0) + quantity
    if requested > product.stock:
        raise _conflict("requested quantity exceeds available stock")

    try:
        if existing is not None:
            existing.qty = requested
        else:
            db.add(CartItem(cart_id=cart.id, product_id=product.id, qty=quantity))
        await db.commit()
    except IntegrityError as exc:
        # The UNIQUE(cart_id, product_id) constraint is the last line of defence if two
        # requests race past the read above.
        await db.rollback()
        raise _conflict("cart item already exists") from exc

    return await get_cart(db, customer_id, shop_id)


async def update_item(
    db: DbSession, customer_id: int, shop_id: int, item_id: int, quantity: int
) -> CartResponse:
    cart = await repo.get_cart(db, customer_id, shop_id)
    if cart is None:
        raise _NOT_FOUND
    item = await repo.get_cart_item(db, cart.id, item_id)
    if item is None:
        raise _NOT_FOUND

    product = await _sellable_product(db, shop_id, item.product_id)
    if quantity > product.stock:
        raise _conflict("requested quantity exceeds available stock")

    item.qty = quantity
    await db.commit()
    return await get_cart(db, customer_id, shop_id)


async def remove_item(db: DbSession, customer_id: int, shop_id: int, item_id: int) -> CartResponse:
    cart = await repo.get_cart(db, customer_id, shop_id)
    if cart is None:
        raise _NOT_FOUND
    item = await repo.get_cart_item(db, cart.id, item_id)
    if item is None:
        raise _NOT_FOUND
    # Removing through the relationship lets delete-orphan issue the DELETE; calling
    # session.delete() directly fights the cascade and leaves the row in place.
    cart.items.remove(item)
    await db.commit()
    return await get_cart(db, customer_id, shop_id)


async def clear_cart(db: DbSession, customer_id: int, shop_id: int) -> CartResponse:
    """Items go, the cart row stays — checkout then always has a cart to work against."""
    cart = await repo.get_cart(db, customer_id, shop_id)
    if cart is None:
        return to_cart_response(None, shop_id)
    cart.items.clear()
    await db.commit()
    return await get_cart(db, customer_id, shop_id)


# --- favorites ------------------------------------------------------------

def to_favorite_response(favorite: Favorite) -> FavoriteResponse:
    product = favorite.product
    return FavoriteResponse(
        product_id=product.id,
        shop_id=favorite.shop_id,
        product_name=product.name,
        image_url=_first_image(product),
        price=product.price,
        discount_price=product.discount_price,
        display_price=_display_price(product),
        in_stock=product.stock > 0,
        # Kept in the list even when the seller deactivates it, but clearly marked.
        is_available=product.is_active and product.stock > 0,
        created_at=favorite.created_at,
    )


async def add_favorite(db: DbSession, customer_id: int, product_id: int) -> FavoriteResponse:
    """Idempotent: favouriting twice returns the existing row rather than erroring."""
    from app.repositories import customer_catalog as catalog_repo

    existing = await repo.get_favorite(db, customer_id, product_id)
    if existing is not None:
        return to_favorite_response(existing)

    product = await catalog_repo.get_any_product(db, product_id)
    if product is None or not product.is_active:
        raise _NOT_FOUND

    favorite = Favorite(customer_id=customer_id, product_id=product.id, shop_id=product.shop_id)
    db.add(favorite)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await repo.get_favorite(db, customer_id, product_id)
        if existing is None:  # pragma: no cover - defensive
            raise
        return to_favorite_response(existing)

    stored = await repo.get_favorite(db, customer_id, product_id)
    if stored is None:  # pragma: no cover - defensive
        raise _NOT_FOUND
    return to_favorite_response(stored)


async def remove_favorite(db: DbSession, customer_id: int, product_id: int) -> None:
    favorite = await repo.get_favorite(db, customer_id, product_id)
    if favorite is None:
        raise _NOT_FOUND
    await db.delete(favorite)
    await db.commit()
