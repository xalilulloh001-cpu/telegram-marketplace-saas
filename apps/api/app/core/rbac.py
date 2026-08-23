"""Role-based permissions for shop members.

Permissions are declared here so later phases attach endpoints to permissions instead of
re-checking roles inline. OWNER is a superset of ADMIN, which is a superset of MANAGER.
"""
from enum import Enum

from app.models.enums import ShopMemberRole


class Permission(str, Enum):
    PRODUCT_VIEW = "product:view"
    PRODUCT_WRITE = "product:write"
    CATEGORY_WRITE = "category:write"
    ORDER_VIEW = "order:view"
    ORDER_UPDATE = "order:update"
    CUSTOMER_VIEW = "customer:view"
    DISCOUNT_WRITE = "discount:write"
    SHOP_SETTINGS_WRITE = "shop:settings:write"
    MEMBER_VIEW = "shop:member:view"
    MEMBER_MANAGE = "shop:member:manage"
    SUBSCRIPTION_MANAGE = "shop:subscription:manage"


_MANAGER: frozenset[Permission] = frozenset(
    {
        Permission.PRODUCT_VIEW,
        Permission.PRODUCT_WRITE,
        Permission.CATEGORY_WRITE,
        Permission.ORDER_VIEW,
        Permission.ORDER_UPDATE,
        Permission.CUSTOMER_VIEW,
    }
)

_ADMIN: frozenset[Permission] = _MANAGER | frozenset(
    {Permission.DISCOUNT_WRITE, Permission.SHOP_SETTINGS_WRITE, Permission.MEMBER_VIEW}
)

_OWNER: frozenset[Permission] = _ADMIN | frozenset(
    {Permission.MEMBER_MANAGE, Permission.SUBSCRIPTION_MANAGE}
)

ROLE_PERMISSIONS: dict[ShopMemberRole, frozenset[Permission]] = {
    ShopMemberRole.OWNER: _OWNER,
    ShopMemberRole.ADMIN: _ADMIN,
    ShopMemberRole.MANAGER: _MANAGER,
}


def role_has_permission(role: ShopMemberRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
