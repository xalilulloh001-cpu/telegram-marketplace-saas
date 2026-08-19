"""Schema-level guarantees for Phase 2: tenant isolation columns and snapshot fields."""
from app.db.base import Base
from app.models import Order, OrderItem

TENANT_SCOPED_TABLES = {
    "shop_members",
    "categories",
    "products",
    "product_images",
    "carts",
    "favorites",
    "orders",
    "subscriptions",
}

GLOBAL_TABLES = {"users", "customers", "addresses", "plans", "platform_admins"}


def test_tenant_tables_carry_shop_id() -> None:
    tables = Base.metadata.tables
    for name in TENANT_SCOPED_TABLES:
        assert "shop_id" in tables[name].columns, f"{name} must be shop-scoped"


def test_global_tables_have_no_shop_id() -> None:
    tables = Base.metadata.tables
    for name in GLOBAL_TABLES:
        assert "shop_id" not in tables[name].columns, f"{name} must stay global"


def test_order_number_is_unique_per_shop_not_globally() -> None:
    constraint_columns = {
        tuple(sorted(c.name for c in constraint.columns))
        for constraint in Order.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("order_number", "shop_id") in constraint_columns


def test_order_items_snapshot_price_and_name() -> None:
    columns = OrderItem.__table__.columns
    assert not columns["price_snapshot"].nullable
    assert not columns["product_name_snapshot"].nullable
