"""Pydantic v2 models for ``featuredpromo.get``, ``featuredpromo.products.get``, and ``promotion.info.get``."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from typing import Any, Optional, Union

from pydantic import Field, field_validator

from ..utils import unwrap_xml_list
from .common import (
    AliExpressBaseModel,
    AliExpressRequestModel,
    FeaturedPromoSortBy,
    parse_optional_decimal,
)
from .products import ProductsResponse


class GetFeaturedPromosRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.featuredpromo.get``."""

    app_signature: Optional[str] = Field(default=None, alias="app_signature")
    fields: Optional[str] = Field(default=None, alias="fields")


class FeaturedPromo(AliExpressBaseModel):
    """Featured promotion entry returned by ``aliexpress.affiliate.featuredpromo.get``."""

    promo_name: str = Field(..., alias="promo_name")
    promo_description: Optional[str] = Field(default=None, alias="promo_desc")
    product_count: Optional[int] = Field(default=None, alias="product_num")

    @property
    def name(self) -> str:
        """Clean alias for :attr:`promo_name`."""
        return self.promo_name

    @property
    def promo_desc(self) -> Optional[str]:
        """Raw alias for :attr:`promo_description`."""
        return self.promo_description

    @property
    def product_num(self) -> Optional[int]:
        """Raw alias for :attr:`product_count`."""
        return self.product_count


class FeaturedPromosResponse(AliExpressBaseModel):
    """Internal API envelope for ``aliexpress.affiliate.featuredpromo.get``."""

    current_record_count: int = Field(default=0, alias="current_record_count")
    promos: list[FeaturedPromo] = Field(default_factory=list, alias="promos")

    @field_validator("promos", mode="before")
    @classmethod
    def _unwrap_promos(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "promo")


class GetFeaturedPromoProductsRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.featuredpromo.products.get``."""

    app_signature: Optional[str] = Field(default=None, alias="app_signature")
    category_id: Optional[str] = Field(default=None, alias="category_id")
    country: Optional[str] = Field(default=None, alias="country")
    fields: Optional[str] = Field(default=None, alias="fields")
    page_no: Optional[int] = Field(default=None, alias="page_no", ge=1)
    page_size: Optional[int] = Field(default=None, alias="page_size", ge=1, le=50)
    promotion_end_time: Optional[str] = Field(default=None, alias="promotion_end_time")
    promotion_name: Optional[str] = Field(default=None, alias="promotion_name")
    promotion_start_time: Optional[str] = Field(default=None, alias="promotion_start_time")
    sort: Optional[Union[FeaturedPromoSortBy, str]] = Field(default=None, alias="sort")
    target_currency: Optional[str] = Field(default=None, alias="target_currency")
    target_language: Optional[str] = Field(default=None, alias="target_language")
    tracking_id: Optional[str] = Field(default=None, alias="tracking_id")


FeaturedPromoProductsResponse = ProductsResponse


class GetPromotionInfoRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.promotion.info.get``."""

    product_id: str = Field(..., alias="product_id")
    ship_to_country: str = Field(..., alias="ship_to_country")
    currency: str = Field(..., alias="currency")
    target_language: str = Field(..., alias="target_language")


class PromotionCoupon(AliExpressBaseModel):
    """Single applicable coupon or promotion inside ``aliexpress.affiliate.promotion.info.get``."""

    coupon_value_type: Optional[str] = Field(default=None, alias="coupon_value_type")
    promotion_effective_dates: Optional[str] = Field(
        default=None, alias="promotion_effective_dates"
    )
    offer_type: Optional[str] = Field(default=None, alias="offer_type")
    money_off_amount: Optional[str] = Field(default=None, alias="money_off_amount")
    minimum_purchase_amount: Optional[str] = Field(default=None, alias="minimum_purchase_amount")
    redemption_channel: Optional[str] = Field(default=None, alias="redemption_channel")
    redemption_code: Optional[str] = Field(default=None, alias="generic_redemption_code")
    product_applicability: Optional[str] = Field(default=None, alias="product_applicability")
    title: Optional[str] = Field(default=None, alias="long_title")

    @property
    def generic_redemption_code(self) -> Optional[str]:
        """Raw alias for :attr:`redemption_code`."""
        return self.redemption_code

    @property
    def long_title(self) -> Optional[str]:
        """Raw alias for :attr:`title`."""
        return self.title

    @property
    def money_off_decimal(self) -> Optional[Decimal]:
        """Parsed numeric :class:`Decimal` for :attr:`money_off_amount` (e.g. ``Decimal('5.00')`` for ``'5.00 USD'``)."""
        return parse_optional_decimal(self.money_off_amount)

    @property
    def minimum_purchase_decimal(self) -> Optional[Decimal]:
        """Parsed numeric :class:`Decimal` for :attr:`minimum_purchase_amount`."""
        return parse_optional_decimal(self.minimum_purchase_amount)


class ProductPromotionResult(AliExpressBaseModel):
    """Domain model for promotions belonging to a single product ID (``aliexpress.affiliate.promotion.info.get``)."""

    product_id: int = Field(..., alias="product_id")
    promotions: list[PromotionCoupon] = Field(default_factory=list, alias="promotions")

    @field_validator("promotions", mode="before")
    @classmethod
    def _unwrap_promotions(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "promotion")

    def __len__(self) -> int:
        return len(self.promotions)

    def __iter__(self) -> Iterator[PromotionCoupon]:  # type: ignore[override]
        return iter(self.promotions)

    def __getitem__(self, index: int) -> PromotionCoupon:
        return self.promotions[index]


class PromotionInfoResponse(AliExpressBaseModel):
    """Internal API envelope for ``aliexpress.affiliate.promotion.info.get``."""

    promotion_results: list[ProductPromotionResult] = Field(
        default_factory=list, alias="promotion_results"
    )

    @field_validator("promotion_results", mode="before")
    @classmethod
    def _unwrap_promotion_results(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "promotion_result")
