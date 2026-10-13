"""Synchronous and asynchronous clients for the AliExpress Affiliate API."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from types import TracebackType
from typing import Optional, Union

import httpx

from ._http import AsyncTransport, SyncTransport
from .config import ClientConfig
from .models.categories import Category, ChildCategory
from .models.common import (
    Currency,
    CursorPage,
    FeaturedPromoSortBy,
    Language,
    LinkType,
    LocaleSite,
    OrderStatus,
    OrderTimeType,
    Page,
    ProductType,
    SortBy,
)
from .models.links import AffiliateLink
from .models.orders import Order
from .models.products import Product, ProductShippingInfo, ProductSkuDetail
from .models.promotions import FeaturedPromo, ProductPromotionResult
from .resources.categories import AsyncCategoriesResource, CategoriesResource
from .resources.links import AsyncLinksResource, LinksResource
from .resources.orders import AsyncOrdersResource, OrdersResource
from .resources.products import AsyncProductsResource, ProductsResource
from .resources.promotions import AsyncPromotionsResource, PromotionsResource

__all__ = [
    "AliExpressClient",
    "AliexpressApi",
    "AsyncAliExpressClient",
]


class _BaseClientMixin:
    """Shared configuration initialization and safe ``__repr__`` for sync and async clients."""

    config: ClientConfig

    @staticmethod
    def _build_client_config(
        *,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        tracking_id: Optional[str] = None,
        language: Optional[Union[Language, str]] = None,
        currency: Optional[Union[Currency, str]] = None,
        country: Optional[str] = None,
        app_signature: Optional[str] = None,
        session: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        raise_on_empty: bool = False,
        key: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> ClientConfig:
        return ClientConfig.from_env_or_args(
            app_key=app_key if app_key is not None else key,
            app_secret=app_secret if app_secret is not None else secret,
            tracking_id=tracking_id,
            language=language,
            currency=currency,
            country=country,
            app_signature=app_signature,
            session=session,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            raise_on_empty=raise_on_empty,
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"app_key={self.config.app_key!r}, "
            f"tracking_id={self.config.tracking_id!r}, "
            f"language={self.config.language!r}, "
            f"currency={self.config.currency!r}, "
            f"country={self.config.country!r})"
        )


class AliExpressClient(_BaseClientMixin):
    """Synchronous client for the AliExpress Affiliate (AE Affiliate) API.

    Exposes both modular resource namespaces (:attr:`links`, :attr:`categories`,
    :attr:`products`, :attr:`orders`, :attr:`promotions`) and top-level convenience
    methods for all 15 official AE Affiliate endpoints.

    Design guarantees:
    - Single-item methods (e.g. :meth:`get_product_details`, :meth:`get_order_details`,
      :meth:`generate_affiliate_link`, :meth:`get_product_sku_details`,
      :meth:`get_product_shipping_info`, :meth:`get_promotion_info`, :meth:`get_category`)
      accept a single identifier and return a single domain model (or raise a specific
      ``*NotFoundError``).
    - Batch and list methods return ``list[Model]``, :class:`Page[Model]`, or
      :class:`CursorPage[Model]` — raw API envelopes never leak into public return values.

    Args:
        app_key: AliExpress Open Platform App Key (or ``ALIEXPRESS_APP_KEY`` env var).
        app_secret: AliExpress Open Platform App Secret (or ``ALIEXPRESS_APP_SECRET`` env var).
        tracking_id: Default affiliate tracking ID (or ``ALIEXPRESS_TRACKING_ID`` env var).
        language: Default target language (default ``Language.EN`` or ``ALIEXPRESS_LANGUAGE``).
        currency: Default target currency (default ``Currency.USD`` or ``ALIEXPRESS_CURRENCY``).
        country: Default destination country code (or ``ALIEXPRESS_COUNTRY`` env var).
        app_signature: Optional legacy API signature string.
        session: Optional TOP session / access token.
        base_url: Gateway base URL (defaults to ``"https://api-sg.aliexpress.com"``).
        timeout: HTTP timeout in seconds (defaults to ``30.0``).
        max_retries: Max retries on transient HTTP/network failures (defaults to ``3``).
        backoff_factor: Exponential backoff factor in seconds (defaults to ``0.5``).
        raise_on_empty: Raise :class:`ResourceNotFoundError` when list queries return 0 records.
        http_client: Optional custom :class:`httpx.Client` instance.
        key: Alias for ``app_key`` (for compatibility with ``python-aliexpress-api``).
        secret: Alias for ``app_secret`` (for compatibility with ``python-aliexpress-api``).

    Example:
        ```python
        from aliexpress_affiliate import AliExpressClient, Currency, Language

        with AliExpressClient(
            app_key="YOUR_KEY",
            app_secret="YOUR_SECRET",
            tracking_id="default",
            language=Language.EN,
            currency=Currency.USD,
            country="US",
        ) as client:
            product = client.get_product_details("33006951782")
            print(product.product_id, product.product_title)
        ```
    """

    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        *,
        tracking_id: Optional[str] = None,
        language: Optional[Union[Language, str]] = None,
        currency: Optional[Union[Currency, str]] = None,
        country: Optional[str] = None,
        app_signature: Optional[str] = None,
        session: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        raise_on_empty: bool = False,
        http_client: Optional[httpx.Client] = None,
        key: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> None:
        self.config: ClientConfig = self._build_client_config(
            app_key=app_key,
            app_secret=app_secret,
            tracking_id=tracking_id,
            language=language,
            currency=currency,
            country=country,
            app_signature=app_signature,
            session=session,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            raise_on_empty=raise_on_empty,
            key=key,
            secret=secret,
        )
        self._transport: SyncTransport = SyncTransport(self.config, http_client=http_client)
        self.links: LinksResource = LinksResource(self._transport)
        self.categories: CategoriesResource = CategoriesResource(self._transport)
        self.products: ProductsResource = ProductsResource(self._transport)
        self.orders: OrdersResource = OrdersResource(self._transport)
        self.promotions: PromotionsResource = PromotionsResource(self._transport)

    def close(self) -> None:
        """Close the underlying synchronous HTTP client."""
        self._transport.close()

    def __enter__(self) -> AliExpressClient:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    # -------------------------------------------------------------------------
    # 1. aliexpress.affiliate.link.generate (single & batch)
    # -------------------------------------------------------------------------
    def generate_affiliate_link(
        self,
        source_value: str,
        *,
        promotion_link_type: Union[LinkType, int] = LinkType.NORMAL,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> AffiliateLink:
        """Generate a single affiliate promotion link for one URL (``aliexpress.affiliate.link.generate``).

        Args:
            source_value: Single product or page URL string.
            promotion_link_type: ``LinkType.NORMAL`` (0) or ``LinkType.HOTLINK`` (2).
            tracking_id: Optional tracking ID override.
            ship_to_country: Optional destination country code override.
            app_signature: Optional API signature override.

        Returns:
            Single :class:`AffiliateLink` domain model.

        Raises:
            ValidationError: If ``source_value`` is not a single URL or ``tracking_id`` is missing.
            LinkGenerationError: If the API returns no promotion link for ``source_value``.

        Example:
            ```python
            link = client.generate_affiliate_link("https://www.aliexpress.com/item/33006951782.html")
            print(link.promotion_link)
            ```
        """
        return self.links.generate_one(
            source_value,
            promotion_link_type=promotion_link_type,
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )

    def get_affiliate_links(
        self,
        links: Union[str, Sequence[str]],
        link_type: Union[LinkType, int] = LinkType.NORMAL,
        *,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> list[AffiliateLink]:
        """Batch generate affiliate promotion links for one or more URLs (``aliexpress.affiliate.link.generate``).

        Example:
            ```python
            links = client.get_affiliate_links(["https://www.aliexpress.com/item/33006951782.html"])
            print(links[0].promotion_link)
            ```
        """
        return self.links.get_affiliate_links(
            links,
            link_type=link_type,
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )

    def generate_affiliate_links(
        self,
        source_values: Union[str, Sequence[str]],
        *,
        promotion_link_type: Union[LinkType, int] = LinkType.NORMAL,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> list[AffiliateLink]:
        """Batch generate affiliate promotion links (alias for :meth:`get_affiliate_links`)."""
        return self.links.generate(
            source_values,
            promotion_link_type=promotion_link_type,
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 2. aliexpress.affiliate.category.get (single & list helpers)
    # -------------------------------------------------------------------------
    def get_category(
        self,
        category_id: Union[int, str],
        *,
        use_cache: bool = True,
        app_signature: Optional[str] = None,
    ) -> Category:
        """Get a single :class:`Category` by its numeric ``category_id``.

        Raises:
            CategoryNotFoundError: If no category with ``category_id`` exists.

        Example:
            ```python
            cat = client.get_category(200000345)
            ```
        """
        return self.categories.get_detail(
            category_id, use_cache=use_cache, app_signature=app_signature
        )

    def get_categories(
        self,
        *,
        app_signature: Optional[str] = None,
    ) -> list[Category]:
        """Get all available categories, both parent and child (``aliexpress.affiliate.category.get``).

        Example:
            ```python
            cats = client.get_categories()
            ```
        """
        return self.categories.get_categories(app_signature=app_signature)

    def get_parent_categories(
        self,
        use_cache: bool = True,
        *,
        app_signature: Optional[str] = None,
    ) -> list[Category]:
        """Get all top-level parent categories.

        Example:
            ```python
            parents = client.get_parent_categories()
            ```
        """
        return self.categories.get_parent_categories(
            use_cache=use_cache, app_signature=app_signature
        )

    def get_child_categories(
        self,
        parent_category_id: Union[int, str],
        use_cache: bool = True,
        *,
        app_signature: Optional[str] = None,
    ) -> list[ChildCategory]:
        """Get all child categories for a given ``parent_category_id``.

        Example:
            ```python
            children = client.get_child_categories(200000345)
            ```
        """
        return self.categories.get_child_categories(
            parent_category_id, use_cache=use_cache, app_signature=app_signature
        )

    # -------------------------------------------------------------------------
    # 3. aliexpress.affiliate.featuredpromo.get
    # -------------------------------------------------------------------------
    def get_featured_promos(
        self,
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> list[FeaturedPromo]:
        """Get active featured promotions as a list of :class:`FeaturedPromo` models (``aliexpress.affiliate.featuredpromo.get``).

        Example:
            ```python
            promos = client.get_featured_promos()
            ```
        """
        return self.promotions.get_featured_promos(fields=fields, app_signature=app_signature)

    # -------------------------------------------------------------------------
    # 4. aliexpress.affiliate.featuredpromo.products.get
    # -------------------------------------------------------------------------
    def get_featured_promo_products(
        self,
        *,
        promotion_name: Optional[str] = None,
        category_id: Optional[Union[str, int]] = None,
        promotion_start_time: Optional[str] = None,
        promotion_end_time: Optional[str] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        sort: Optional[Union[FeaturedPromoSortBy, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Get paginated products from a featured promotion (``aliexpress.affiliate.featuredpromo.products.get``).

        Example:
            ```python
            page = client.get_featured_promo_products(promotion_name="Hot Product")
            ```
        """
        return self.promotions.get_featured_promo_products(
            promotion_name=promotion_name,
            category_id=category_id,
            promotion_start_time=promotion_start_time,
            promotion_end_time=promotion_end_time,
            page_no=page_no,
            page_size=page_size,
            sort=sort,
            fields=fields,
            country=country,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 5. aliexpress.affiliate.hotproduct.download
    # -------------------------------------------------------------------------
    def download_hot_products(
        self,
        category_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        locale_site: Optional[Union[LocaleSite, str]] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Download paginated hot products by category (``aliexpress.affiliate.hotproduct.download``).

        Example:
            ```python
            page = client.download_hot_products(category_id="200000345")
            ```
        """
        return self.products.download_hot(
            category_id,
            fields=fields,
            locale_site=locale_site,
            page_no=page_no,
            page_size=page_size,
            country=country,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 6. aliexpress.affiliate.hotproduct.query
    # -------------------------------------------------------------------------
    def get_hot_products(
        self,
        *,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        keywords: Optional[str] = None,
        max_sale_price: Optional[int] = None,
        min_sale_price: Optional[int] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        platform_product_type: Optional[Union[ProductType, str]] = None,
        promotion_name: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        sort: Optional[Union[SortBy, str]] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Query high-commission hot products (``aliexpress.affiliate.hotproduct.query``).

        Example:
            ```python
            page = client.get_hot_products(keywords="earbuds", page_size=10)
            ```
        """
        return self.products.query_hot(
            keywords=keywords,
            category_ids=category_ids,
            delivery_days=delivery_days,
            fields=fields,
            max_sale_price=max_sale_price,
            min_sale_price=min_sale_price,
            page_no=page_no,
            page_size=page_size,
            platform_product_type=platform_product_type,
            promotion_name=promotion_name,
            ship_to_country=ship_to_country,
            sort=sort,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    get_hotproducts = get_hot_products

    # -------------------------------------------------------------------------
    # 7. aliexpress.affiliate.product.query
    # -------------------------------------------------------------------------
    def get_products(
        self,
        *,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        keywords: Optional[str] = None,
        max_sale_price: Optional[int] = None,
        min_sale_price: Optional[int] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        platform_product_type: Optional[Union[ProductType, str]] = None,
        promotion_name: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        sort: Optional[Union[SortBy, str]] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Search for affiliate products (``aliexpress.affiliate.product.query``).

        Example:
            ```python
            page = client.get_products(keywords="gaming mouse", sort=SortBy.SALE_PRICE_ASC)
            ```
        """
        return self.products.query(
            keywords=keywords,
            category_ids=category_ids,
            delivery_days=delivery_days,
            fields=fields,
            max_sale_price=max_sale_price,
            min_sale_price=min_sale_price,
            page_no=page_no,
            page_size=page_size,
            platform_product_type=platform_product_type,
            promotion_name=promotion_name,
            ship_to_country=ship_to_country,
            sort=sort,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    query_products = get_products

    # -------------------------------------------------------------------------
    # 8. aliexpress.affiliate.productdetail.get (single & batch)
    # -------------------------------------------------------------------------
    def get_product_details(
        self,
        product_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Product:
        """Get detailed product information for ONE product ID or URL (``aliexpress.affiliate.productdetail.get``).

        Args:
            product_id: Single product ID (``int`` or ``str``) or AliExpress item URL.
            fields: Optional response field list.
            country: Optional destination country code.
            target_currency: Currency override.
            target_language: Language override.
            tracking_id: Tracking ID override.
            app_signature: Optional API signature override.

        Returns:
            Single :class:`Product` domain model.

        Raises:
            ValidationError: If multiple IDs or a sequence is passed instead of a single ID.
            ProductNotFoundError: If the API returns no product for ``product_id``.

        Example:
            ```python
            product = client.get_product_details("33006951782")
            print(product.product_id, product.product_title)
            ```
        """
        return self.products.get_detail(
            product_id,
            fields=fields,
            country=country,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    def get_products_details(
        self,
        product_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> list[Product]:
        """Batch lookup detailed product information for multiple product IDs or URLs (``aliexpress.affiliate.productdetail.get``).

        Args:
            product_ids: Sequence or comma-separated string of product IDs or AliExpress item URLs.
            fields: Optional response field list.
            country: Optional destination country code.
            target_currency: Currency override.
            target_language: Language override.
            tracking_id: Tracking ID override.
            app_signature: Optional API signature override.

        Returns:
            List of :class:`Product` domain models.

        Example:
            ```python
            products = client.get_products_details(["33006951782", "1005004757833857"])
            ```
        """
        return self.products.get_details(
            product_ids,
            fields=fields,
            country=country,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 9. aliexpress.affiliate.product.smartmatch
    # -------------------------------------------------------------------------
    def smart_match_products(
        self,
        device_id: Optional[str] = None,
        *,
        app: Optional[str] = None,
        country: Optional[str] = None,
        device: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        keywords: Optional[str] = None,
        page_no: Optional[int] = None,
        product_id: Optional[Union[str, int]] = None,
        site: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        user: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Smart-match affiliate products (``aliexpress.affiliate.product.smartmatch``).

        Example:
            ```python
            page = client.smart_match_products(device_id="adid-123", keywords="charger")
            ```
        """
        return self.products.smart_match(
            device_id=device_id,
            app=app,
            country=country,
            device=device,
            fields=fields,
            keywords=keywords,
            page_no=page_no,
            product_id=product_id,
            site=site,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            user=user,
            app_signature=app_signature,
        )

    smart_match_product = smart_match_products

    # -------------------------------------------------------------------------
    # 10. aliexpress.affiliate.product.shipping.get
    # -------------------------------------------------------------------------
    def get_product_shipping_info(
        self,
        *,
        product_id: Union[str, int],
        sku_id: Union[str, int],
        target_sale_price: Union[str, float, int, Decimal],
        tax_rate: Union[str, float, Decimal],
        ship_to_country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> ProductShippingInfo:
        """Get product shipping fee and delivery estimate (``aliexpress.affiliate.product.shipping.get``).

        Example:
            ```python
            shipping = client.get_product_shipping_info(
                product_id=33006951782,
                sku_id=12000029786932962,
                ship_to_country="US",
                target_sale_price="15.9",
                tax_rate="0.1",
            )
            ```
        """
        return self.products.get_shipping_info(
            product_id=product_id,
            sku_id=sku_id,
            target_sale_price=target_sale_price,
            tax_rate=tax_rate,
            ship_to_country=ship_to_country,
            target_currency=target_currency,
            target_language=target_language,
        )

    # -------------------------------------------------------------------------
    # 11. aliexpress.affiliate.product.sku.detail.get
    # -------------------------------------------------------------------------
    def get_product_sku_details(
        self,
        product_id: Union[str, int],
        *,
        ship_to_country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        sku_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        need_deliver_info: Optional[Union[bool, str]] = None,
    ) -> ProductSkuDetail:
        """Get SKU-level pricing, specifications, and delivery info for a single product (``aliexpress.affiliate.product.sku.detail.get``).

        Raises:
            ProductNotFoundError: If no SKU or item information is returned for ``product_id``.

        Example:
            ```python
            sku_details = client.get_product_sku_details("1005004757833857", ship_to_country="DE")
            ```
        """
        return self.products.get_sku_details(
            product_id,
            ship_to_country=ship_to_country,
            target_currency=target_currency,
            target_language=target_language,
            sku_ids=sku_ids,
            need_deliver_info=need_deliver_info,
        )

    # -------------------------------------------------------------------------
    # 12. aliexpress.affiliate.promotion.info.get (single & batch)
    # -------------------------------------------------------------------------
    def get_promotion_info(
        self,
        product_id: Union[str, int],
        *,
        ship_to_country: Optional[str] = None,
        currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> ProductPromotionResult:
        """Retrieve real-time applicable coupons and promotions for ONE product (``aliexpress.affiliate.promotion.info.get``).

        Raises:
            ValidationError: If multiple product IDs are passed.
            ProductNotFoundError: If no promotion record is returned for ``product_id``.

        Example:
            ```python
            promo = client.get_promotion_info("1005006067128597", ship_to_country="US")
            for coupon in promo.promotions:
                print(coupon.redemption_code, coupon.money_off_amount)
            ```
        """
        return self.promotions.get_promotion_info(
            product_id,
            ship_to_country=ship_to_country,
            currency=currency,
            target_language=target_language,
        )

    def get_promotions_info(
        self,
        product_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        ship_to_country: Optional[str] = None,
        currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> list[ProductPromotionResult]:
        """Batch retrieve real-time applicable coupons and promotions for up to 10 products (``aliexpress.affiliate.promotion.info.get``).

        Example:
            ```python
            promos = client.get_promotions_info(["1005006067128597", "33006951782"], ship_to_country="US")
            ```
        """
        return self.promotions.get_promotions_info(
            product_ids,
            ship_to_country=ship_to_country,
            currency=currency,
            target_language=target_language,
        )

    # -------------------------------------------------------------------------
    # 13. aliexpress.affiliate.order.get (single & batch)
    # -------------------------------------------------------------------------
    def get_order_details(
        self,
        order_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> Order:
        """Retrieve details for ONE affiliate order or sub-order ID (``aliexpress.affiliate.order.get``).

        Unwraps the API envelope internally so pagination and record-count fields never leak.

        Args:
            order_id: Single order or sub-order ID (``int`` or numeric ``str``).
            fields: Optional response field list.
            app_signature: Optional API signature parameter.

        Returns:
            Single :class:`Order` domain model.

        Raises:
            ValidationError: If multiple order IDs or a sequence is passed.
            OrderNotFoundError: If no order is returned for ``order_id``.

        Example:
            ```python
            order = client.get_order_details(22222)
            print(order.order_id, order.order_status, order.paid_amount)
            ```
        """
        return self.orders.get_detail(order_id, fields=fields, app_signature=app_signature)

    def get_orders_details(
        self,
        order_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> list[Order]:
        """Batch retrieve affiliate orders by multiple order or sub-order IDs (``aliexpress.affiliate.order.get``).

        Args:
            order_ids: Sequence or comma-separated string of order/sub-order IDs.
            fields: Optional response field list.
            app_signature: Optional API signature parameter.

        Returns:
            List of :class:`Order` domain models.

        Example:
            ```python
            orders = client.get_orders_details([22222, 111111])
            ```
        """
        return self.orders.get_details(order_ids, fields=fields, app_signature=app_signature)

    get_order_info = get_orders_details
    get_orders_by_ids = get_orders_details

    # -------------------------------------------------------------------------
    # 14. aliexpress.affiliate.order.list
    # -------------------------------------------------------------------------
    def get_order_list(
        self,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        *,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        locale_site: Optional[Union[LocaleSite, str]] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Order]:
        """Retrieve a paginated list of affiliate orders (``aliexpress.affiliate.order.list``).

        Returns:
            Typed :class:`Page[Order]` with ``items``, ``page_no``, ``page_size``,
            ``total_count``, ``total_pages``, and ``has_next``.

        Example:
            ```python
            page = client.get_order_list(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-07 23:59:59",
            )
            for order in page.items:
                print(order.order_id, order.paid_amount)
            ```
        """
        return self.orders.list(
            status=status,
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            fields=fields,
            locale_site=locale_site,
            page_no=page_no,
            page_size=page_size,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 15. aliexpress.affiliate.order.listbyindex
    # -------------------------------------------------------------------------
    def get_order_list_by_index(
        self,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        *,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        start_query_index_id: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> CursorPage[Order]:
        """Retrieve affiliate orders using cursor/index pagination (``aliexpress.affiliate.order.listbyindex``).

        Returns:
            Typed :class:`CursorPage[Order]` with ``items``, ``min_query_index_id``,
            ``max_query_index_id``, ``page_size``, and ``has_next``.

        Example:
            ```python
            page = client.get_order_list_by_index(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-07 23:59:59",
            )
            ```
        """
        return self.orders.list_by_index(
            status=status,
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            start_query_index_id=start_query_index_id,
            fields=fields,
            page_size=page_size,
            app_signature=app_signature,
        )


class AsyncAliExpressClient(_BaseClientMixin):
    """Asynchronous client for the AliExpress Affiliate (AE Affiliate) API.

    Shares the exact same resource structure, method names, and return types as
    :class:`AliExpressClient`, using ``async`` / ``await`` over :class:`httpx.AsyncClient`.

    Example:
        ```python
        import asyncio
        from aliexpress_affiliate import AsyncAliExpressClient

        async def main() -> None:
            async with AsyncAliExpressClient(
                app_key="YOUR_KEY",
                app_secret="YOUR_SECRET",
                tracking_id="default",
            ) as client:
                product = await client.get_product_details("33006951782")
                print(product.product_id, product.product_title)

        asyncio.run(main())
        ```
    """

    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        *,
        tracking_id: Optional[str] = None,
        language: Optional[Union[Language, str]] = None,
        currency: Optional[Union[Currency, str]] = None,
        country: Optional[str] = None,
        app_signature: Optional[str] = None,
        session: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        raise_on_empty: bool = False,
        http_client: Optional[httpx.AsyncClient] = None,
        key: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> None:
        self.config: ClientConfig = self._build_client_config(
            app_key=app_key,
            app_secret=app_secret,
            tracking_id=tracking_id,
            language=language,
            currency=currency,
            country=country,
            app_signature=app_signature,
            session=session,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            raise_on_empty=raise_on_empty,
            key=key,
            secret=secret,
        )
        self._transport: AsyncTransport = AsyncTransport(self.config, http_client=http_client)
        self.links: AsyncLinksResource = AsyncLinksResource(self._transport)
        self.categories: AsyncCategoriesResource = AsyncCategoriesResource(self._transport)
        self.products: AsyncProductsResource = AsyncProductsResource(self._transport)
        self.orders: AsyncOrdersResource = AsyncOrdersResource(self._transport)
        self.promotions: AsyncPromotionsResource = AsyncPromotionsResource(self._transport)

    async def aclose(self) -> None:
        """Close the underlying asynchronous HTTP client."""
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncAliExpressClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    # -------------------------------------------------------------------------
    # 1. aliexpress.affiliate.link.generate (single & batch)
    # -------------------------------------------------------------------------
    async def generate_affiliate_link(
        self,
        source_value: str,
        *,
        promotion_link_type: Union[LinkType, int] = LinkType.NORMAL,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> AffiliateLink:
        """Asynchronously generate a single affiliate promotion link for one URL."""
        return await self.links.generate_one(
            source_value,
            promotion_link_type=promotion_link_type,
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )

    async def get_affiliate_links(
        self,
        links: Union[str, Sequence[str]],
        link_type: Union[LinkType, int] = LinkType.NORMAL,
        *,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> list[AffiliateLink]:
        """Asynchronously batch generate affiliate promotion links."""
        return await self.links.get_affiliate_links(
            links,
            link_type=link_type,
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )

    async def generate_affiliate_links(
        self,
        source_values: Union[str, Sequence[str]],
        *,
        promotion_link_type: Union[LinkType, int] = LinkType.NORMAL,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> list[AffiliateLink]:
        """Asynchronously batch generate affiliate promotion links (alias for :meth:`get_affiliate_links`)."""
        return await self.links.generate(
            source_values,
            promotion_link_type=promotion_link_type,
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 2. aliexpress.affiliate.category.get (single & list helpers)
    # -------------------------------------------------------------------------
    async def get_category(
        self,
        category_id: Union[int, str],
        *,
        use_cache: bool = True,
        app_signature: Optional[str] = None,
    ) -> Category:
        """Asynchronously get a single :class:`Category` by its numeric ``category_id``."""
        return await self.categories.get_detail(
            category_id, use_cache=use_cache, app_signature=app_signature
        )

    async def get_categories(
        self,
        *,
        app_signature: Optional[str] = None,
    ) -> list[Category]:
        """Asynchronously get all available categories, both parent and child."""
        return await self.categories.get_categories(app_signature=app_signature)

    async def get_parent_categories(
        self,
        use_cache: bool = True,
        *,
        app_signature: Optional[str] = None,
    ) -> list[Category]:
        """Asynchronously get all top-level parent categories."""
        return await self.categories.get_parent_categories(
            use_cache=use_cache, app_signature=app_signature
        )

    async def get_child_categories(
        self,
        parent_category_id: Union[int, str],
        use_cache: bool = True,
        *,
        app_signature: Optional[str] = None,
    ) -> list[ChildCategory]:
        """Asynchronously get all child categories for a given ``parent_category_id``."""
        return await self.categories.get_child_categories(
            parent_category_id, use_cache=use_cache, app_signature=app_signature
        )

    # -------------------------------------------------------------------------
    # 3. aliexpress.affiliate.featuredpromo.get
    # -------------------------------------------------------------------------
    async def get_featured_promos(
        self,
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> list[FeaturedPromo]:
        """Asynchronously get active featured promotions as a list of :class:`FeaturedPromo` models."""
        return await self.promotions.get_featured_promos(fields=fields, app_signature=app_signature)

    # -------------------------------------------------------------------------
    # 4. aliexpress.affiliate.featuredpromo.products.get
    # -------------------------------------------------------------------------
    async def get_featured_promo_products(
        self,
        *,
        promotion_name: Optional[str] = None,
        category_id: Optional[Union[str, int]] = None,
        promotion_start_time: Optional[str] = None,
        promotion_end_time: Optional[str] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        sort: Optional[Union[FeaturedPromoSortBy, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Asynchronously get paginated products from a featured promotion."""
        return await self.promotions.get_featured_promo_products(
            promotion_name=promotion_name,
            category_id=category_id,
            promotion_start_time=promotion_start_time,
            promotion_end_time=promotion_end_time,
            page_no=page_no,
            page_size=page_size,
            sort=sort,
            fields=fields,
            country=country,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 5. aliexpress.affiliate.hotproduct.download
    # -------------------------------------------------------------------------
    async def download_hot_products(
        self,
        category_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        locale_site: Optional[Union[LocaleSite, str]] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Asynchronously download paginated hot products by category."""
        return await self.products.download_hot(
            category_id,
            fields=fields,
            locale_site=locale_site,
            page_no=page_no,
            page_size=page_size,
            country=country,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 6. aliexpress.affiliate.hotproduct.query
    # -------------------------------------------------------------------------
    async def get_hot_products(
        self,
        *,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        keywords: Optional[str] = None,
        max_sale_price: Optional[int] = None,
        min_sale_price: Optional[int] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        platform_product_type: Optional[Union[ProductType, str]] = None,
        promotion_name: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        sort: Optional[Union[SortBy, str]] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Asynchronously query high-commission hot products."""
        return await self.products.query_hot(
            keywords=keywords,
            category_ids=category_ids,
            delivery_days=delivery_days,
            fields=fields,
            max_sale_price=max_sale_price,
            min_sale_price=min_sale_price,
            page_no=page_no,
            page_size=page_size,
            platform_product_type=platform_product_type,
            promotion_name=promotion_name,
            ship_to_country=ship_to_country,
            sort=sort,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    get_hotproducts = get_hot_products

    # -------------------------------------------------------------------------
    # 7. aliexpress.affiliate.product.query
    # -------------------------------------------------------------------------
    async def get_products(
        self,
        *,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        keywords: Optional[str] = None,
        max_sale_price: Optional[int] = None,
        min_sale_price: Optional[int] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        platform_product_type: Optional[Union[ProductType, str]] = None,
        promotion_name: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        sort: Optional[Union[SortBy, str]] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Asynchronously search for affiliate products."""
        return await self.products.query(
            keywords=keywords,
            category_ids=category_ids,
            delivery_days=delivery_days,
            fields=fields,
            max_sale_price=max_sale_price,
            min_sale_price=min_sale_price,
            page_no=page_no,
            page_size=page_size,
            platform_product_type=platform_product_type,
            promotion_name=promotion_name,
            ship_to_country=ship_to_country,
            sort=sort,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    query_products = get_products

    # -------------------------------------------------------------------------
    # 8. aliexpress.affiliate.productdetail.get (single & batch)
    # -------------------------------------------------------------------------
    async def get_product_details(
        self,
        product_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Product:
        """Asynchronously get detailed product information for ONE product ID or URL.

        Raises:
            ValidationError: If multiple IDs or a sequence is passed instead of a single ID.
            ProductNotFoundError: If the API returns no product for ``product_id``.
        """
        return await self.products.get_detail(
            product_id,
            fields=fields,
            country=country,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    async def get_products_details(
        self,
        product_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> list[Product]:
        """Asynchronously batch lookup detailed product information for multiple product IDs or URLs."""
        return await self.products.get_details(
            product_ids,
            fields=fields,
            country=country,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 9. aliexpress.affiliate.product.smartmatch
    # -------------------------------------------------------------------------
    async def smart_match_products(
        self,
        device_id: Optional[str] = None,
        *,
        app: Optional[str] = None,
        country: Optional[str] = None,
        device: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        keywords: Optional[str] = None,
        page_no: Optional[int] = None,
        product_id: Optional[Union[str, int]] = None,
        site: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        user: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Asynchronously smart-match affiliate products."""
        return await self.products.smart_match(
            device_id=device_id,
            app=app,
            country=country,
            device=device,
            fields=fields,
            keywords=keywords,
            page_no=page_no,
            product_id=product_id,
            site=site,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            user=user,
            app_signature=app_signature,
        )

    smart_match_product = smart_match_products

    # -------------------------------------------------------------------------
    # 10. aliexpress.affiliate.product.shipping.get
    # -------------------------------------------------------------------------
    async def get_product_shipping_info(
        self,
        *,
        product_id: Union[str, int],
        sku_id: Union[str, int],
        target_sale_price: Union[str, float, int, Decimal],
        tax_rate: Union[str, float, Decimal],
        ship_to_country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> ProductShippingInfo:
        """Asynchronously get product shipping fee and delivery estimate."""
        return await self.products.get_shipping_info(
            product_id=product_id,
            sku_id=sku_id,
            target_sale_price=target_sale_price,
            tax_rate=tax_rate,
            ship_to_country=ship_to_country,
            target_currency=target_currency,
            target_language=target_language,
        )

    # -------------------------------------------------------------------------
    # 11. aliexpress.affiliate.product.sku.detail.get
    # -------------------------------------------------------------------------
    async def get_product_sku_details(
        self,
        product_id: Union[str, int],
        *,
        ship_to_country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        sku_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        need_deliver_info: Optional[Union[bool, str]] = None,
    ) -> ProductSkuDetail:
        """Asynchronously get SKU-level pricing, specifications, and delivery info."""
        return await self.products.get_sku_details(
            product_id,
            ship_to_country=ship_to_country,
            target_currency=target_currency,
            target_language=target_language,
            sku_ids=sku_ids,
            need_deliver_info=need_deliver_info,
        )

    # -------------------------------------------------------------------------
    # 12. aliexpress.affiliate.promotion.info.get (single & batch)
    # -------------------------------------------------------------------------
    async def get_promotion_info(
        self,
        product_id: Union[str, int],
        *,
        ship_to_country: Optional[str] = None,
        currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> ProductPromotionResult:
        """Asynchronously retrieve real-time applicable coupons and promotions for ONE product."""
        return await self.promotions.get_promotion_info(
            product_id,
            ship_to_country=ship_to_country,
            currency=currency,
            target_language=target_language,
        )

    async def get_promotions_info(
        self,
        product_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        ship_to_country: Optional[str] = None,
        currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> list[ProductPromotionResult]:
        """Asynchronously batch retrieve real-time applicable coupons and promotions for up to 10 products."""
        return await self.promotions.get_promotions_info(
            product_ids,
            ship_to_country=ship_to_country,
            currency=currency,
            target_language=target_language,
        )

    # -------------------------------------------------------------------------
    # 13. aliexpress.affiliate.order.get (single & batch)
    # -------------------------------------------------------------------------
    async def get_order_details(
        self,
        order_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> Order:
        """Asynchronously retrieve details for ONE affiliate order or sub-order ID (``aliexpress.affiliate.order.get``).

        Raises:
            ValidationError: If multiple order IDs or a sequence is passed.
            OrderNotFoundError: If no order is returned for ``order_id``.
        """
        return await self.orders.get_detail(order_id, fields=fields, app_signature=app_signature)

    async def get_orders_details(
        self,
        order_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> list[Order]:
        """Asynchronously batch retrieve affiliate orders by multiple order or sub-order IDs."""
        return await self.orders.get_details(order_ids, fields=fields, app_signature=app_signature)

    get_order_info = get_orders_details
    get_orders_by_ids = get_orders_details

    # -------------------------------------------------------------------------
    # 14. aliexpress.affiliate.order.list
    # -------------------------------------------------------------------------
    async def get_order_list(
        self,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        *,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        locale_site: Optional[Union[LocaleSite, str]] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Order]:
        """Asynchronously retrieve a paginated list of affiliate orders."""
        return await self.orders.list(
            status=status,
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            fields=fields,
            locale_site=locale_site,
            page_no=page_no,
            page_size=page_size,
            app_signature=app_signature,
        )

    # -------------------------------------------------------------------------
    # 15. aliexpress.affiliate.order.listbyindex
    # -------------------------------------------------------------------------
    async def get_order_list_by_index(
        self,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        *,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        start_query_index_id: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> CursorPage[Order]:
        """Asynchronously retrieve affiliate orders using cursor/index pagination."""
        return await self.orders.list_by_index(
            status=status,
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            start_query_index_id=start_query_index_id,
            fields=fields,
            page_size=page_size,
            app_signature=app_signature,
        )


# Compatibility alias matching sergioteula/python-aliexpress-api
AliexpressApi = AliExpressClient
