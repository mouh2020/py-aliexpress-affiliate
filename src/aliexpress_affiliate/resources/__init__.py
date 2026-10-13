"""Resource namespaces for the AliExpress Affiliate API."""

from __future__ import annotations

from .base import AsyncResource, SyncResource
from .categories import (
    AsyncCategoriesResource,
    CategoriesResource,
    filter_child_categories,
    filter_parent_categories,
)
from .links import AsyncLinksResource, LinksResource
from .orders import AsyncOrdersResource, OrdersResource
from .products import AsyncProductsResource, ProductsResource
from .promotions import AsyncPromotionsResource, PromotionsResource

__all__ = [
    "AsyncCategoriesResource",
    "AsyncLinksResource",
    "AsyncOrdersResource",
    "AsyncProductsResource",
    "AsyncPromotionsResource",
    "AsyncResource",
    "CategoriesResource",
    "LinksResource",
    "OrdersResource",
    "ProductsResource",
    "PromotionsResource",
    "SyncResource",
    "filter_child_categories",
    "filter_parent_categories",
]
