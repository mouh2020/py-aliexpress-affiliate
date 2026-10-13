"""Pydantic v2 models for ``aliexpress.affiliate.category.get``."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field, field_validator

from ..utils import unwrap_xml_list
from .common import AliExpressBaseModel, AliExpressRequestModel


class GetCategoriesRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.category.get``."""

    app_signature: Optional[str] = Field(default=None, alias="app_signature")


class Category(AliExpressBaseModel):
    """AliExpress Affiliate product category.

    Attributes:
        category_id: Unique numeric identifier of the category.
        category_name: Display name of the category.
        parent_category_id: Parent category ID if this is a child category, otherwise ``None``.
    """

    category_id: int = Field(..., alias="category_id")
    category_name: str = Field(..., alias="category_name")
    parent_category_id: Optional[int] = Field(default=None, alias="parent_category_id")

    @property
    def id(self) -> int:
        """Clean alias for :attr:`category_id`."""
        return self.category_id

    @property
    def name(self) -> str:
        """Clean alias for :attr:`category_name`."""
        return self.category_name

    @property
    def parent_id(self) -> Optional[int]:
        """Clean alias for :attr:`parent_category_id`."""
        return self.parent_category_id

    @property
    def is_parent(self) -> bool:
        """Return ``True`` if this category is a top-level parent category."""
        return self.parent_category_id is None


class ChildCategory(Category):
    """Child category with a guaranteed non-null ``parent_category_id``."""

    parent_category_id: int = Field(..., alias="parent_category_id")


class CategoriesResponse(AliExpressBaseModel):
    """Internal API envelope for ``aliexpress.affiliate.category.get``."""

    total_result_count: int = Field(default=0, alias="total_result_count")
    categories: list[Category] = Field(default_factory=list, alias="categories")

    @field_validator("categories", mode="before")
    @classmethod
    def _unwrap_categories(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "category")
