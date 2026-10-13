"""Pydantic v2 models for all product, hotproduct, detail, smartmatch, shipping, and SKU endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Union

from pydantic import Field, field_validator

from ..utils import unwrap_xml_list
from .common import (
    AliExpressBaseModel,
    AliExpressRequestModel,
    Page,
    PaginatedResult,
    ProductType,
    SortBy,
    parse_optional_datetime,
    parse_optional_decimal,
)


class PromoCodeInfo(AliExpressBaseModel):
    """Embedded promotional coupon code info attached to an affiliate product."""

    promo_code: Optional[str] = Field(default=None, alias="promo_code")
    code_campaign_type: Optional[str] = Field(default=None, alias="code_campaigntype")
    code_value: Optional[str] = Field(default=None, alias="code_value")
    code_available_time_start: Optional[str] = Field(default=None, alias="code_availabletime_start")
    code_available_time_end: Optional[str] = Field(default=None, alias="code_availabletime_end")
    code_minimum_spend: Optional[str] = Field(default=None, alias="code_mini_spend")
    code_quantity: Optional[int] = Field(default=None, alias="code_quantity")
    code_promotion_url: Optional[str] = Field(default=None, alias="code_promotionurl")

    @property
    def available_start_datetime(self) -> Optional[datetime]:
        """Parsed :class:`datetime` for :attr:`code_available_time_start`."""
        return parse_optional_datetime(self.code_available_time_start)

    @property
    def available_end_datetime(self) -> Optional[datetime]:
        """Parsed :class:`datetime` for :attr:`code_available_time_end`."""
        return parse_optional_datetime(self.code_available_time_end)

    @property
    def minimum_spend_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`code_minimum_spend`."""
        return parse_optional_decimal(self.code_minimum_spend)

    @property
    def code_campaigntype(self) -> Optional[str]:
        """Backwards-compatible alias for :attr:`code_campaign_type`."""
        return self.code_campaign_type

    @property
    def code_availabletime_start(self) -> Optional[str]:
        """Backwards-compatible alias for :attr:`code_available_time_start`."""
        return self.code_available_time_start

    @property
    def code_availabletime_end(self) -> Optional[str]:
        """Backwards-compatible alias for :attr:`code_available_time_end`."""
        return self.code_available_time_end

    @property
    def code_mini_spend(self) -> Optional[str]:
        """Backwards-compatible alias for :attr:`code_minimum_spend`."""
        return self.code_minimum_spend

    @property
    def code_promotionurl(self) -> Optional[str]:
        """Backwards-compatible alias for :attr:`code_promotion_url`."""
        return self.code_promotion_url


class Product(AliExpressBaseModel):
    """Affiliate product returned by query, hotproduct, detail, featuredpromo, and smartmatch APIs.

    Note:
        AliExpress spells the 30-day sales volume field ``lastest_volume`` in its JSON payload.
        Both :attr:`latest_volume` (clean attribute) and :attr:`lastest_volume` (official alias)
        are supported seamlessly. Price and rate fields are preserved as raw strings and also
        exposed as exact :class:`Decimal` properties (e.g. :attr:`target_sale_price_decimal`,
        :attr:`commission_rate_pct`).
    """

    product_id: int = Field(..., alias="product_id")
    sku_id: Optional[int] = Field(default=None, alias="sku_id")
    product_title: Optional[str] = Field(default=None, alias="product_title")
    product_detail_url: Optional[str] = Field(default=None, alias="product_detail_url")
    product_main_image_url: Optional[str] = Field(default=None, alias="product_main_image_url")
    product_small_image_urls: list[str] = Field(
        default_factory=list, alias="product_small_image_urls"
    )
    product_video_url: Optional[str] = Field(default=None, alias="product_video_url")
    promotion_link: Optional[str] = Field(default=None, alias="promotion_link")

    app_sale_price: Optional[str] = Field(default=None, alias="app_sale_price")
    app_sale_price_currency: Optional[str] = Field(default=None, alias="app_sale_price_currency")
    original_price: Optional[str] = Field(default=None, alias="original_price")
    original_price_currency: Optional[str] = Field(default=None, alias="original_price_currency")
    sale_price: Optional[str] = Field(default=None, alias="sale_price")
    sale_price_currency: Optional[str] = Field(default=None, alias="sale_price_currency")

    target_app_sale_price: Optional[str] = Field(default=None, alias="target_app_sale_price")
    target_app_sale_price_currency: Optional[str] = Field(
        default=None, alias="target_app_sale_price_currency"
    )
    target_original_price: Optional[str] = Field(default=None, alias="target_original_price")
    target_original_price_currency: Optional[str] = Field(
        default=None, alias="target_original_price_currency"
    )
    target_sale_price: Optional[str] = Field(default=None, alias="target_sale_price")
    target_sale_price_currency: Optional[str] = Field(
        default=None, alias="target_sale_price_currency"
    )

    commission_rate: Optional[str] = Field(default=None, alias="commission_rate")
    hot_product_commission_rate: Optional[str] = Field(
        default=None, alias="hot_product_commission_rate"
    )
    relevant_market_commission_rate: Optional[str] = Field(
        default=None, alias="relevant_market_commission_rate"
    )
    discount: Optional[str] = Field(default=None, alias="discount")
    evaluate_rate: Optional[str] = Field(default=None, alias="evaluate_rate")
    latest_volume: Optional[int] = Field(default=None, alias="lastest_volume")

    first_level_category_id: Optional[int] = Field(default=None, alias="first_level_category_id")
    first_level_category_name: Optional[str] = Field(
        default=None, alias="first_level_category_name"
    )
    second_level_category_id: Optional[int] = Field(default=None, alias="second_level_category_id")
    second_level_category_name: Optional[str] = Field(
        default=None, alias="second_level_category_name"
    )

    platform_product_type: Optional[str] = Field(default=None, alias="platform_product_type")
    shop_id: Optional[int] = Field(default=None, alias="shop_id")
    shop_name: Optional[str] = Field(default=None, alias="shop_name")
    shop_url: Optional[str] = Field(default=None, alias="shop_url")
    tax_rate: Optional[str] = Field(default=None, alias="tax_rate")
    ean_code: Optional[str] = Field(default=None, alias="ean_code")
    ship_to_days: Optional[str] = Field(default=None, alias="ship_to_days")
    promo_code_info: Optional[PromoCodeInfo] = Field(default=None, alias="promo_code_info")

    @field_validator("product_small_image_urls", mode="before")
    @classmethod
    def _unwrap_small_images(cls, value: Any) -> list[str]:
        items = unwrap_xml_list(value, "string")
        return [str(item) for item in items if item is not None]

    @property
    def id(self) -> int:
        """Clean alias for :attr:`product_id`."""
        return self.product_id

    @property
    def title(self) -> Optional[str]:
        """Clean alias for :attr:`product_title`."""
        return self.product_title

    @property
    def lastest_volume(self) -> Optional[int]:
        """Backwards-compatible alias for :attr:`latest_volume` (AliExpress typo in API)."""
        return self.latest_volume

    @property
    def sale_price_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`sale_price`."""
        return parse_optional_decimal(self.sale_price)

    @property
    def original_price_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`original_price`."""
        return parse_optional_decimal(self.original_price)

    @property
    def app_sale_price_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`app_sale_price`."""
        return parse_optional_decimal(self.app_sale_price)

    @property
    def target_sale_price_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`target_sale_price`."""
        return parse_optional_decimal(self.target_sale_price)

    @property
    def target_original_price_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`target_original_price`."""
        return parse_optional_decimal(self.target_original_price)

    @property
    def target_app_sale_price_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`target_app_sale_price`."""
        return parse_optional_decimal(self.target_app_sale_price)

    @property
    def commission_rate_pct(self) -> Optional[Decimal]:
        """Parsed percentage :class:`Decimal` for :attr:`commission_rate` (e.g. ``Decimal('3.5')`` for ``'3.5%'``)."""
        return parse_optional_decimal(self.commission_rate)

    @property
    def hot_product_commission_rate_pct(self) -> Optional[Decimal]:
        """Parsed percentage :class:`Decimal` for :attr:`hot_product_commission_rate`."""
        return parse_optional_decimal(self.hot_product_commission_rate)

    @property
    def discount_pct(self) -> Optional[Decimal]:
        """Parsed percentage :class:`Decimal` for :attr:`discount`."""
        return parse_optional_decimal(self.discount)

    @property
    def evaluate_rate_pct(self) -> Optional[Decimal]:
        """Parsed percentage :class:`Decimal` for :attr:`evaluate_rate`."""
        return parse_optional_decimal(self.evaluate_rate)

    @property
    def tax_rate_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`tax_rate`."""
        return parse_optional_decimal(self.tax_rate)


class ProductQueryRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.product.query`` and ``hotproduct.query``."""

    app_signature: Optional[str] = Field(default=None, alias="app_signature")
    category_ids: Optional[str] = Field(default=None, alias="category_ids")
    delivery_days: Optional[str] = Field(default=None, alias="delivery_days")
    fields: Optional[str] = Field(default=None, alias="fields")
    keywords: Optional[str] = Field(default=None, alias="keywords")
    max_sale_price: Optional[int] = Field(default=None, alias="max_sale_price")
    min_sale_price: Optional[int] = Field(default=None, alias="min_sale_price")
    page_no: Optional[int] = Field(default=None, alias="page_no", ge=1)
    page_size: Optional[int] = Field(default=None, alias="page_size", ge=1, le=50)
    platform_product_type: Optional[Union[ProductType, str]] = Field(
        default=None, alias="platform_product_type"
    )
    promotion_name: Optional[str] = Field(default=None, alias="promotion_name")
    ship_to_country: Optional[str] = Field(default=None, alias="ship_to_country")
    sort: Optional[Union[SortBy, str]] = Field(default=None, alias="sort")
    target_currency: Optional[str] = Field(default=None, alias="target_currency")
    target_language: Optional[str] = Field(default=None, alias="target_language")
    tracking_id: Optional[str] = Field(default=None, alias="tracking_id")


class HotProductDownloadRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.hotproduct.download``."""

    category_id: str = Field(..., alias="category_id")
    app_signature: Optional[str] = Field(default=None, alias="app_signature")
    country: Optional[str] = Field(default=None, alias="country")
    fields: Optional[str] = Field(default=None, alias="fields")
    locale_site: Optional[str] = Field(default=None, alias="locale_site")
    page_no: Optional[int] = Field(default=None, alias="page_no", ge=1)
    page_size: Optional[int] = Field(default=None, alias="page_size", ge=1, le=50)
    target_currency: Optional[str] = Field(default=None, alias="target_currency")
    target_language: Optional[str] = Field(default=None, alias="target_language")
    tracking_id: Optional[str] = Field(default=None, alias="tracking_id")


class ProductDetailRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.productdetail.get``."""

    product_ids: str = Field(..., alias="product_ids")
    app_signature: Optional[str] = Field(default=None, alias="app_signature")
    country: Optional[str] = Field(default=None, alias="country")
    fields: Optional[str] = Field(default=None, alias="fields")
    target_currency: Optional[str] = Field(default=None, alias="target_currency")
    target_language: Optional[str] = Field(default=None, alias="target_language")
    tracking_id: Optional[str] = Field(default=None, alias="tracking_id")


class SmartMatchProductsRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.product.smartmatch``."""

    device_id: Optional[str] = Field(default=None, alias="device_id")
    app: Optional[str] = Field(default=None, alias="app")
    app_signature: Optional[str] = Field(default=None, alias="app_signature")
    country: Optional[str] = Field(default=None, alias="country")
    device: Optional[str] = Field(default=None, alias="device")
    fields: Optional[str] = Field(default=None, alias="fields")
    keywords: Optional[str] = Field(default=None, alias="keywords")
    page_no: Optional[int] = Field(default=None, alias="page_no", ge=1)
    product_id: Optional[str] = Field(default=None, alias="product_id")
    site: Optional[str] = Field(default=None, alias="site")
    target_currency: Optional[str] = Field(default=None, alias="target_currency")
    target_language: Optional[str] = Field(default=None, alias="target_language")
    tracking_id: Optional[str] = Field(default=None, alias="tracking_id")
    user: Optional[str] = Field(default=None, alias="user")


class ProductsResponse(PaginatedResult):
    """Internal API envelope for product list and detail endpoints."""

    is_finished: Optional[bool] = Field(default=None, alias="is_finished")
    products: list[Product] = Field(default_factory=list, alias="products")

    @field_validator("products", mode="before")
    @classmethod
    def _unwrap_products(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "product")

    def to_page(
        self,
        *,
        requested_page_no: Optional[int] = None,
        requested_page_size: Optional[int] = None,
    ) -> Page[Product]:
        """Convert this raw API envelope into a clean :class:`Page[Product]`."""
        return Page[Product](
            items=self.products,
            page_no=self.current_page_no if self.current_page_no is not None else requested_page_no,
            page_size=(
                requested_page_size
                if requested_page_size is not None
                else (self.current_record_count or len(self.products))
            ),
            total_count=self.total_record_count,
            total_pages=self.total_page_no,
            is_finished=self.is_finished,
        )


HotProductsResponse = ProductsResponse


class ProductShippingRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.product.shipping.get``."""

    product_id: int = Field(..., alias="product_id")
    sku_id: int = Field(..., alias="sku_id")
    ship_to_country: str = Field(..., alias="ship_to_country")
    target_currency: str = Field(..., alias="target_currency")
    target_sale_price: str = Field(..., alias="target_sale_price")
    target_language: str = Field(..., alias="target_language")
    tax_rate: str = Field(..., alias="tax_rate")


class ProductShippingInfo(AliExpressBaseModel):
    """Shipping cost and delivery estimate returned by ``aliexpress.affiliate.product.shipping.get``."""

    shipping_fee: Optional[str] = Field(default=None, alias="shipping_fee")
    delivery_days: Optional[int] = Field(default=None, alias="delivery_days")
    min_delivery_days: Optional[int] = Field(default=None, alias="min_delivery_days")
    max_delivery_days: Optional[int] = Field(default=None, alias="max_delivery_days")
    ship_from_country: Optional[str] = Field(default=None, alias="ship_from_country")

    @property
    def shipping_fee_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`shipping_fee`."""
        return parse_optional_decimal(self.shipping_fee)


class ProductSkuDetailRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.product.sku.detail.get``."""

    product_id: str = Field(..., alias="product_id")
    ship_to_country: str = Field(..., alias="ship_to_country")
    target_currency: str = Field(..., alias="target_currency")
    target_language: str = Field(..., alias="target_language")
    need_deliver_info: Optional[str] = Field(default=None, alias="need_deliver_info")
    sku_ids: Optional[str] = Field(default=None, alias="sku_ids")


class SkuItemInfo(AliExpressBaseModel):
    """Product-level attribute metadata inside ``aliexpress.affiliate.product.sku.detail.get``."""

    product_id: int = Field(..., alias="product_id")
    title: Optional[str] = Field(default=None, alias="title")
    english_title: Optional[str] = Field(default=None, alias="en_title")
    original_link: Optional[str] = Field(default=None, alias="original_link")
    image_link: Optional[str] = Field(default=None, alias="image_link")
    image_white: Optional[str] = Field(default=None, alias="image_white")
    additional_image_links: list[str] = Field(default_factory=list, alias="additional_image_links")
    product_category: Optional[str] = Field(default=None, alias="product_category")
    product_score: Optional[str] = Field(default=None, alias="product_score")
    review_number: Optional[int] = Field(default=None, alias="review_number")
    order_number: Optional[int] = Field(default=None, alias="order_number")
    brand: Optional[str] = Field(default=None, alias="brand")
    store_name: Optional[str] = Field(default=None, alias="store_name")
    condition: Optional[str] = Field(default=None, alias="condition")
    gender: Optional[str] = Field(default=None, alias="gender")
    age_group: Optional[str] = Field(default=None, alias="age_group")
    display_category_id_l1: Optional[int] = Field(default=None, alias="display_category_id_l1")
    display_category_name_l1: Optional[str] = Field(default=None, alias="display_category_name_l1")
    display_category_id_l2: Optional[int] = Field(default=None, alias="display_category_id_l2")
    display_category_name_l2: Optional[str] = Field(default=None, alias="display_category_name_l2")
    display_category_id_l3: Optional[int] = Field(default=None, alias="display_category_id_l3")
    display_category_name_l3: Optional[str] = Field(default=None, alias="display_category_name_l3")
    display_category_id_l4: Optional[int] = Field(default=None, alias="display_category_id_l4")
    display_category_name_l4: Optional[str] = Field(default=None, alias="display_category_name_l4")

    @field_validator("additional_image_links", mode="before")
    @classmethod
    def _unwrap_additional_images(cls, value: Any) -> list[str]:
        items = unwrap_xml_list(value, "string")
        return [str(item) for item in items if item is not None]

    @property
    def en_title(self) -> Optional[str]:
        """Alias for :attr:`english_title`."""
        return self.english_title

    @property
    def product_score_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`product_score`."""
        return parse_optional_decimal(self.product_score)


class SkuVariantInfo(AliExpressBaseModel):
    """Single SKU variant details inside ``aliexpress.affiliate.product.sku.detail.get``."""

    sku_id: int = Field(..., alias="sku_id")
    link: Optional[str] = Field(default=None, alias="link")
    sku_image_link: Optional[str] = Field(default=None, alias="sku_image_link")
    color: Optional[str] = Field(default=None, alias="color")
    size: Optional[str] = Field(default=None, alias="size")
    sku_properties: Optional[str] = Field(default=None, alias="sku_properties")
    currency: Optional[str] = Field(default=None, alias="currency")
    price_with_tax: Optional[str] = Field(default=None, alias="price_with_tax")
    sale_price_with_tax: Optional[str] = Field(default=None, alias="sale_price_with_tax")
    discount_rate: Optional[str] = Field(default=None, alias="discount_rate")
    tax_rate: Optional[str] = Field(default=None, alias="tax_rate")
    shipping_fees: Optional[str] = Field(default=None, alias="shipping_fees")
    ship_from_country: Optional[str] = Field(default=None, alias="ship_from_country")
    delivery_days: Optional[int] = Field(default=None, alias="delivery_days")
    min_delivery_days: Optional[int] = Field(default=None, alias="min_delivery_days")
    max_delivery_days: Optional[int] = Field(default=None, alias="max_delivery_days")
    ean_code: Optional[str] = Field(default=None, alias="ean_code")

    @property
    def price_with_tax_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`price_with_tax`."""
        return parse_optional_decimal(self.price_with_tax)

    @property
    def sale_price_with_tax_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`sale_price_with_tax`."""
        return parse_optional_decimal(self.sale_price_with_tax)

    @property
    def shipping_fees_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`shipping_fees`."""
        return parse_optional_decimal(self.shipping_fees)

    @property
    def discount_rate_pct(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`discount_rate`."""
        return parse_optional_decimal(self.discount_rate)

    @property
    def tax_rate_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`tax_rate`."""
        return parse_optional_decimal(self.tax_rate)


class ProductSkuDetail(AliExpressBaseModel):
    """Domain model for SKU-level product details (``aliexpress.affiliate.product.sku.detail.get``).

    Maps ``ae_item_info`` -> :attr:`item_info` and ``ae_item_sku_info`` -> :attr:`skus`
    while keeping the raw aliases accessible.
    """

    item_info: Optional[SkuItemInfo] = Field(default=None, alias="ae_item_info")
    skus: list[SkuVariantInfo] = Field(default_factory=list, alias="ae_item_sku_info")

    @field_validator("skus", mode="before")
    @classmethod
    def _unwrap_skus(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(
            value,
            "traffic_sku_info_list",
            "ae_item_sku_info_d_t_o",
            "sku_info",
        )

    @property
    def product_id(self) -> Optional[int]:
        """Product ID from :attr:`item_info` if available."""
        return self.item_info.product_id if self.item_info is not None else None

    @property
    def ae_item_info(self) -> Optional[SkuItemInfo]:
        """Raw alias for :attr:`item_info`."""
        return self.item_info

    @property
    def ae_item_sku_info(self) -> list[SkuVariantInfo]:
        """Raw alias for :attr:`skus`."""
        return self.skus


# Backwards-compatible alias
ProductSkuDetailResponse = ProductSkuDetail
