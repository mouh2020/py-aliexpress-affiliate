"""Products resource covering 7 AliExpress Affiliate product, hotproduct, shipping, and SKU endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Optional, Union

from ..exceptions import ProductNotFoundError, ResourceNotFoundError, ValidationError
from ..models.common import Currency, Language, LocaleSite, Page, ProductType, SortBy
from ..models.products import (
    HotProductDownloadRequest,
    HotProductsResponse,
    Product,
    ProductDetailRequest,
    ProductQueryRequest,
    ProductShippingInfo,
    ProductShippingRequest,
    ProductSkuDetail,
    ProductSkuDetailRequest,
    ProductsResponse,
    SmartMatchProductsRequest,
)
from ..utils import extract_product_id, format_csv_param, normalize_product_ids
from .base import AsyncResource, SyncResource

__all__ = [
    "API_HOTPRODUCT_DOWNLOAD",
    "API_HOTPRODUCT_QUERY",
    "API_PRODUCTDETAIL_GET",
    "API_PRODUCT_QUERY",
    "API_PRODUCT_SHIPPING_GET",
    "API_PRODUCT_SKU_DETAIL_GET",
    "API_PRODUCT_SMARTMATCH",
    "AsyncProductsResource",
    "ProductsResource",
]

API_PRODUCT_QUERY: str = "aliexpress.affiliate.product.query"
API_HOTPRODUCT_QUERY: str = "aliexpress.affiliate.hotproduct.query"
API_HOTPRODUCT_DOWNLOAD: str = "aliexpress.affiliate.hotproduct.download"
API_PRODUCTDETAIL_GET: str = "aliexpress.affiliate.productdetail.get"
API_PRODUCT_SMARTMATCH: str = "aliexpress.affiliate.product.smartmatch"
API_PRODUCT_SHIPPING_GET: str = "aliexpress.affiliate.product.shipping.get"
API_PRODUCT_SKU_DETAIL_GET: str = "aliexpress.affiliate.product.sku.detail.get"


class _ProductsMixin:
    """Shared request builders and response unwrappers for all product-related endpoints."""

    def _build_product_query_request(
        self,
        *,
        keywords: Optional[str] = None,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        max_sale_price: Optional[int] = None,
        min_sale_price: Optional[int] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        platform_product_type: Optional[Union[ProductType, str]] = None,
        promotion_name: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        sort: Optional[Union[SortBy, str]] = None,
        target_currency: Optional[str] = None,
        target_language: Optional[str] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> ProductQueryRequest:
        return ProductQueryRequest(
            app_signature=app_signature,
            category_ids=format_csv_param(category_ids),
            delivery_days=str(delivery_days) if delivery_days is not None else None,
            fields=format_csv_param(fields),
            keywords=keywords,
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
        )

    def _build_hotproduct_download_request(
        self,
        category_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        locale_site: Optional[Union[LocaleSite, str]] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        country: Optional[str] = None,
        target_currency: Optional[str] = None,
        target_language: Optional[str] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> HotProductDownloadRequest:
        site_val = locale_site.value if isinstance(locale_site, LocaleSite) else locale_site
        return HotProductDownloadRequest(
            category_id=str(category_id),
            app_signature=app_signature,
            country=country,
            fields=format_csv_param(fields),
            locale_site=site_val,
            page_no=page_no,
            page_size=page_size,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
        )

    def _build_product_detail_request(
        self,
        product_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        country: Optional[str] = None,
        target_currency: Optional[str] = None,
        target_language: Optional[str] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> ProductDetailRequest:
        normalized_ids = normalize_product_ids(product_ids)
        return ProductDetailRequest(
            product_ids=normalized_ids,
            app_signature=app_signature,
            country=country,
            fields=format_csv_param(fields),
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
        )

    def _build_smart_match_request(
        self,
        *,
        device_id: Optional[str] = None,
        keywords: Optional[str] = None,
        product_id: Optional[Union[str, int]] = None,
        page_no: Optional[int] = None,
        app: Optional[str] = None,
        country: Optional[str] = None,
        device: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        site: Optional[str] = None,
        target_currency: Optional[str] = None,
        target_language: Optional[str] = None,
        tracking_id: Optional[str] = None,
        user: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> SmartMatchProductsRequest:
        extracted_pid = extract_product_id(product_id) if product_id is not None else None
        if not device_id and not keywords and not extracted_pid:
            raise ValidationError(
                "At least one of 'device_id', 'keywords', or 'product_id' must be provided "
                "for smart_match"
            )
        return SmartMatchProductsRequest(
            device_id=device_id,
            app=app,
            app_signature=app_signature,
            country=country,
            device=device,
            fields=format_csv_param(fields),
            keywords=keywords,
            page_no=page_no,
            product_id=extracted_pid,
            site=site,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
            user=user,
        )

    def _build_shipping_request(
        self,
        *,
        product_id: Union[str, int],
        sku_id: Union[str, int],
        ship_to_country: str,
        target_sale_price: Union[str, float, int, Decimal],
        tax_rate: Union[str, float, Decimal],
        target_currency: str,
        target_language: str,
    ) -> ProductShippingRequest:
        extracted_pid = int(extract_product_id(product_id))
        extracted_sku = int(extract_product_id(sku_id))
        return ProductShippingRequest(
            product_id=extracted_pid,
            sku_id=extracted_sku,
            ship_to_country=ship_to_country,
            target_currency=target_currency,
            target_sale_price=str(target_sale_price),
            target_language=target_language,
            tax_rate=str(tax_rate),
        )

    def _build_sku_detail_request(
        self,
        product_id: Union[str, int],
        *,
        ship_to_country: str,
        target_currency: str,
        target_language: str,
        sku_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        need_deliver_info: Optional[Union[bool, str]] = None,
    ) -> ProductSkuDetailRequest:
        extracted_pid = extract_product_id(product_id)
        deliver_flag: Optional[str] = None
        if isinstance(need_deliver_info, bool):
            deliver_flag = "Yes" if need_deliver_info else "No"
        elif isinstance(need_deliver_info, str):
            deliver_flag = need_deliver_info
        return ProductSkuDetailRequest(
            product_id=extracted_pid,
            ship_to_country=ship_to_country,
            target_currency=target_currency,
            target_language=target_language,
            need_deliver_info=deliver_flag,
            sku_ids=format_csv_param(sku_ids),
        )

    @staticmethod
    def _empty_product_page(
        page_no: Optional[int],
        page_size: Optional[int] = None,
        *,
        default_page_no: Optional[int] = 1,
        raise_on_empty: bool,
    ) -> Page[Product]:
        if raise_on_empty:
            raise
        return Page[Product](
            items=[],
            page_no=page_no if page_no is not None else default_page_no,
            page_size=page_size or 0,
            total_count=0,
            total_pages=0,
        )

    @staticmethod
    def _finalize_product_page(
        envelope: ProductsResponse,
        *,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        raise_on_empty: bool,
    ) -> Page[Product]:
        if raise_on_empty and not envelope.products:
            raise ResourceNotFoundError("No products found with current parameters")
        return envelope.to_page(requested_page_no=page_no, requested_page_size=page_size)

    @staticmethod
    def _unwrap_single_product(envelope: ProductsResponse, single_id: str) -> Product:
        if not envelope.products:
            raise ProductNotFoundError(single_id)
        return envelope.products[0]

    @staticmethod
    def _unwrap_batch_products(
        envelope: ProductsResponse,
        *,
        raise_on_empty: bool,
    ) -> list[Product]:
        if raise_on_empty and not envelope.products:
            raise ProductNotFoundError(message="No products found for the requested product_ids")
        return envelope.products

    @staticmethod
    def _handle_batch_products_not_found(
        exc: ResourceNotFoundError,
        *,
        raise_on_empty: bool,
    ) -> list[Product]:
        if raise_on_empty:
            raise ProductNotFoundError(
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return []

    @staticmethod
    def _finalize_sku_detail(detail: ProductSkuDetail, single_id: str) -> ProductSkuDetail:
        if detail.item_info is None and not detail.skus:
            raise ProductNotFoundError(single_id)
        return detail


class ProductsResource(SyncResource, _ProductsMixin):
    """Synchronous resource for all 7 AliExpress Affiliate product endpoints."""

    def query(
        self,
        *,
        keywords: Optional[str] = None,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
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

        Args:
            keywords: Search keywords (e.g., ``"wireless earbuds"``).
            category_ids: Category ID or list of category IDs.
            delivery_days: Estimated delivery days filter (e.g., ``3``, ``5``, ``7``, ``10``).
            fields: Comma-separated or list of response fields to include.
            max_sale_price: Maximum sale price in cents (e.g., ``3141`` for ``$31.41``).
            min_sale_price: Minimum sale price in cents.
            page_no: Page number (>= 1).
            page_size: Page size (1 to 50).
            platform_product_type: ``ProductType.ALL``, ``PLAZA``, or ``TMALL``.
            promotion_name: Featured promotion name filter.
            ship_to_country: Two-letter destination country code.
            sort: ``SortBy`` enum or sort string (``SALE_PRICE_ASC``, etc.).
            target_currency: Currency override (defaults to client's ``currency``).
            target_language: Language override (defaults to client's ``language``).
            tracking_id: Tracking ID override (defaults to client's ``tracking_id``).
            app_signature: Optional API signature override.

        Returns:
            Typed :class:`Page[Product]` containing ``items``, ``page_no``, ``page_size``,
            ``total_count``, ``total_pages``, and ``has_next``.

        Example:
            ```python
            page = client.products.query(keywords="mechanical keyboard", page_size=10)
            for item in page.items:
                print(item.product_id, item.product_title, item.target_sale_price)
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_product_query_request(
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
            ship_to_country=self._resolve_country(ship_to_country),
            sort=sort,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_PRODUCT_QUERY, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError:
            return self._empty_product_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_product_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    def query_hot(
        self,
        *,
        keywords: Optional[str] = None,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
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

        Returns:
            Typed :class:`Page[Product]` containing hot affiliate products.

        Example:
            ```python
            hot_page = client.products.query_hot(keywords="smartwatch", sort=SortBy.LAST_VOLUME_DESC)
            print(len(hot_page.items))
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_product_query_request(
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
            ship_to_country=self._resolve_country(ship_to_country),
            sort=sort,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_HOTPRODUCT_QUERY, req.to_api_params(), HotProductsResponse
            )
        except ResourceNotFoundError:
            return self._empty_product_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_product_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    def download_hot(
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
        """Download hot products by category (``aliexpress.affiliate.hotproduct.download``).

        Returns:
            Typed :class:`Page[Product]` containing the downloaded hot products.

        Example:
            ```python
            page = client.products.download_hot(category_id="200000345", page_size=20)
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_hotproduct_download_request(
            category_id,
            fields=fields,
            locale_site=locale_site,
            page_no=page_no,
            page_size=page_size,
            country=self._resolve_country(country, param_name="country"),
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_HOTPRODUCT_DOWNLOAD, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError:
            return self._empty_product_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_product_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    def get_detail(
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
        """Get detailed product information for a single product ID or URL (``aliexpress.affiliate.productdetail.get``).

        Args:
            product_id: Single product ID (``int`` or ``str``) or AliExpress item URL.
            fields: Optional response fields to include.
            country: Optional destination country code for localized pricing/tax.
            target_currency: Currency override.
            target_language: Language override.
            tracking_id: Tracking ID override.
            app_signature: Optional API signature override.

        Returns:
            Single :class:`Product` domain model.

        Raises:
            ValidationError: If ``product_id`` is a sequence, comma-separated, or invalid.
            ProductNotFoundError: If the API returns no product for ``product_id``.

        Example:
            ```python
            product = client.products.get_detail("33006951782")
            print(product.product_id, product.product_title)
            ```
        """
        single_id = extract_product_id(product_id)
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_product_detail_request(
            single_id,
            fields=fields,
            country=self._resolve_country(country, param_name="country"),
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_PRODUCTDETAIL_GET, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError as exc:
            raise ProductNotFoundError(
                single_id,
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return self._unwrap_single_product(envelope, single_id)

    def get_details(
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
            fields: Optional response fields to include.
            country: Optional destination country code for localized pricing/tax.
            target_currency: Currency override.
            target_language: Language override.
            tracking_id: Tracking ID override.
            app_signature: Optional API signature override.

        Returns:
            List of :class:`Product` domain models.

        Example:
            ```python
            products = client.products.get_details(
                ["33006951782", "https://www.aliexpress.com/item/1005004757833857.html"]
            )
            for p in products:
                print(p.product_id, p.product_title)
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_product_detail_request(
            product_ids,
            fields=fields,
            country=self._resolve_country(country, param_name="country"),
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_PRODUCTDETAIL_GET, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError as exc:
            return self._handle_batch_products_not_found(
                exc, raise_on_empty=self.config.raise_on_empty
            )
        return self._unwrap_batch_products(envelope, raise_on_empty=self.config.raise_on_empty)

    def smart_match(
        self,
        *,
        device_id: Optional[str] = None,
        keywords: Optional[str] = None,
        product_id: Optional[Union[str, int]] = None,
        page_no: Optional[int] = None,
        app: Optional[str] = None,
        country: Optional[str] = None,
        device: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        site: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        user: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Smart-match affiliate products based on keywords, product ID, or device (``aliexpress.affiliate.product.smartmatch``).

        Note:
            Fixes the tuple bug ``request.app = app,`` present in ``sergioteula/python-aliexpress-api``.

        Returns:
            Typed :class:`Page[Product]` containing matched products.

        Example:
            ```python
            matched = client.products.smart_match(device_id="anon-device-1", keywords="bluetooth speaker")
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_smart_match_request(
            device_id=device_id,
            keywords=keywords,
            product_id=product_id,
            page_no=page_no,
            app=app,
            country=self._resolve_country(country, param_name="country"),
            device=device,
            fields=fields,
            site=site,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            user=user,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_PRODUCT_SMARTMATCH, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError:
            return self._empty_product_page(
                page_no, default_page_no=None, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_product_page(
            envelope, page_no=page_no, raise_on_empty=self.config.raise_on_empty
        )

    def get_shipping_info(
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
        """Get product shipping fee and delivery days (``aliexpress.affiliate.product.shipping.get``).

        Args:
            product_id: Single product ID or URL.
            sku_id: Single SKU ID (obtained from product query or detail API).
            target_sale_price: Non-App sale price in target currency.
            tax_rate: Product tax rate (obtained from product query or detail API, e.g. ``"0.1"``).
            ship_to_country: Two-letter destination country code (defaults to client's ``country``).
            target_currency: Target currency (defaults to client's ``currency``).
            target_language: Target language (defaults to client's ``language``).

        Returns:
            Single :class:`ProductShippingInfo` domain model.

        Example:
            ```python
            shipping = client.products.get_shipping_info(
                product_id=33006951782,
                sku_id=12000029786932962,
                ship_to_country="US",
                target_sale_price="15.9",
                tax_rate="0.1",
            )
            print(shipping.shipping_fee, shipping.delivery_days)
            ```
        """
        single_id = extract_product_id(product_id)
        resolved_country = self._resolve_country(
            ship_to_country, required=True, param_name="ship_to_country"
        )
        assert resolved_country is not None
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_shipping_request(
            product_id=single_id,
            sku_id=sku_id,
            ship_to_country=resolved_country,
            target_sale_price=target_sale_price,
            tax_rate=tax_rate,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
        )
        try:
            return self._transport.request_model(
                API_PRODUCT_SHIPPING_GET, req.to_api_params(), ProductShippingInfo
            )
        except ResourceNotFoundError as exc:
            raise ProductNotFoundError(
                single_id,
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc

    def get_sku_details(
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

        Args:
            product_id: Single product ID or URL.
            ship_to_country: Destination country code (defaults to client's ``country``).
            target_currency: Target currency (defaults to client's ``currency``).
            target_language: Target language (defaults to client's ``language``).
            sku_ids: Optional comma-separated string or list of SKU IDs (max 20 returned if omitted).
            need_deliver_info: ``True`` / ``"Yes"`` or ``False`` / ``"No"`` (default ``"No"``).

        Returns:
            Single :class:`ProductSkuDetail` domain model with :attr:`item_info` and :attr:`skus`.

        Raises:
            ValidationError: If ``product_id`` is invalid or ``ship_to_country`` is missing.
            ProductNotFoundError: If no SKU or item information is returned for ``product_id``.

        Example:
            ```python
            sku_detail = client.products.get_sku_details(
                "1005004757833857",
                ship_to_country="DE",
                need_deliver_info=True,
            )
            for sku in sku_detail.skus:
                print(sku.sku_id, sku.color, sku.size, sku.sale_price_with_tax)
            ```
        """
        single_id = extract_product_id(product_id)
        resolved_country = self._resolve_country(
            ship_to_country, required=True, param_name="ship_to_country"
        )
        assert resolved_country is not None
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_sku_detail_request(
            single_id,
            ship_to_country=resolved_country,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            sku_ids=sku_ids,
            need_deliver_info=need_deliver_info,
        )
        try:
            detail = self._transport.request_model(
                API_PRODUCT_SKU_DETAIL_GET, req.to_api_params(), ProductSkuDetail
            )
        except ResourceNotFoundError as exc:
            raise ProductNotFoundError(
                single_id,
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return self._finalize_sku_detail(detail, single_id)


class AsyncProductsResource(AsyncResource, _ProductsMixin):
    """Asynchronous resource for all 7 AliExpress Affiliate product endpoints."""

    async def query(
        self,
        *,
        keywords: Optional[str] = None,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
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
        """Asynchronously search for affiliate products (``aliexpress.affiliate.product.query``).

        Example:
            ```python
            page = await async_client.products.query(keywords="usb c hub", page_size=10)
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_product_query_request(
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
            ship_to_country=self._resolve_country(ship_to_country),
            sort=sort,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_PRODUCT_QUERY, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError:
            return self._empty_product_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_product_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    async def query_hot(
        self,
        *,
        keywords: Optional[str] = None,
        category_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        delivery_days: Optional[Union[int, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
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
        """Asynchronously query high-commission hot products (``aliexpress.affiliate.hotproduct.query``).

        Example:
            ```python
            hot_page = await async_client.products.query_hot(keywords="headphones")
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_product_query_request(
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
            ship_to_country=self._resolve_country(ship_to_country),
            sort=sort,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_HOTPRODUCT_QUERY, req.to_api_params(), HotProductsResponse
            )
        except ResourceNotFoundError:
            return self._empty_product_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_product_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    async def download_hot(
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
        """Asynchronously download hot products by category (``aliexpress.affiliate.hotproduct.download``).

        Example:
            ```python
            page = await async_client.products.download_hot("200000345")
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_hotproduct_download_request(
            category_id,
            fields=fields,
            locale_site=locale_site,
            page_no=page_no,
            page_size=page_size,
            country=self._resolve_country(country, param_name="country"),
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_HOTPRODUCT_DOWNLOAD, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError:
            return self._empty_product_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_product_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    async def get_detail(
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
        """Asynchronously get detailed product information for a single product ID or URL.

        Raises:
            ValidationError: If ``product_id`` is a sequence, comma-separated, or invalid.
            ProductNotFoundError: If the API returns no product for ``product_id``.

        Example:
            ```python
            product = await async_client.products.get_detail("33006951782")
            ```
        """
        single_id = extract_product_id(product_id)
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_product_detail_request(
            single_id,
            fields=fields,
            country=self._resolve_country(country, param_name="country"),
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_PRODUCTDETAIL_GET, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError as exc:
            raise ProductNotFoundError(
                single_id,
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return self._unwrap_single_product(envelope, single_id)

    async def get_details(
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
        """Asynchronously batch lookup detailed product information (``aliexpress.affiliate.productdetail.get``).

        Example:
            ```python
            products = await async_client.products.get_details(["33006951782", "1005004757833857"])
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_product_detail_request(
            product_ids,
            fields=fields,
            country=self._resolve_country(country, param_name="country"),
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_PRODUCTDETAIL_GET, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError as exc:
            return self._handle_batch_products_not_found(
                exc, raise_on_empty=self.config.raise_on_empty
            )
        return self._unwrap_batch_products(envelope, raise_on_empty=self.config.raise_on_empty)

    async def smart_match(
        self,
        *,
        device_id: Optional[str] = None,
        keywords: Optional[str] = None,
        product_id: Optional[Union[str, int]] = None,
        page_no: Optional[int] = None,
        app: Optional[str] = None,
        country: Optional[str] = None,
        device: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        site: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        tracking_id: Optional[str] = None,
        user: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Product]:
        """Asynchronously smart-match affiliate products (``aliexpress.affiliate.product.smartmatch``).

        Example:
            ```python
            matched = await async_client.products.smart_match(device_id="dev-1", keywords="drone")
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_smart_match_request(
            device_id=device_id,
            keywords=keywords,
            product_id=product_id,
            page_no=page_no,
            app=app,
            country=self._resolve_country(country, param_name="country"),
            device=device,
            fields=fields,
            site=site,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            user=user,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_PRODUCT_SMARTMATCH, req.to_api_params(), ProductsResponse
            )
        except ResourceNotFoundError:
            return self._empty_product_page(
                page_no, default_page_no=None, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_product_page(
            envelope, page_no=page_no, raise_on_empty=self.config.raise_on_empty
        )

    async def get_shipping_info(
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
        """Asynchronously get product shipping fee and delivery days (``aliexpress.affiliate.product.shipping.get``).

        Example:
            ```python
            shipping = await async_client.products.get_shipping_info(
                product_id=33006951782,
                sku_id=12000029786932962,
                ship_to_country="US",
                target_sale_price="15.9",
                tax_rate="0.1",
            )
            ```
        """
        single_id = extract_product_id(product_id)
        resolved_country = self._resolve_country(
            ship_to_country, required=True, param_name="ship_to_country"
        )
        assert resolved_country is not None
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_shipping_request(
            product_id=single_id,
            sku_id=sku_id,
            ship_to_country=resolved_country,
            target_sale_price=target_sale_price,
            tax_rate=tax_rate,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
        )
        try:
            return await self._transport.request_model(
                API_PRODUCT_SHIPPING_GET, req.to_api_params(), ProductShippingInfo
            )
        except ResourceNotFoundError as exc:
            raise ProductNotFoundError(
                single_id,
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc

    async def get_sku_details(
        self,
        product_id: Union[str, int],
        *,
        ship_to_country: Optional[str] = None,
        target_currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
        sku_ids: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        need_deliver_info: Optional[Union[bool, str]] = None,
    ) -> ProductSkuDetail:
        """Asynchronously get SKU-level pricing, specifications, and delivery info (``aliexpress.affiliate.product.sku.detail.get``).

        Example:
            ```python
            sku_detail = await async_client.products.get_sku_details(
                "1005004757833857",
                ship_to_country="DE",
            )
            ```
        """
        single_id = extract_product_id(product_id)
        resolved_country = self._resolve_country(
            ship_to_country, required=True, param_name="ship_to_country"
        )
        assert resolved_country is not None
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_sku_detail_request(
            single_id,
            ship_to_country=resolved_country,
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            sku_ids=sku_ids,
            need_deliver_info=need_deliver_info,
        )
        try:
            detail = await self._transport.request_model(
                API_PRODUCT_SKU_DETAIL_GET, req.to_api_params(), ProductSkuDetail
            )
        except ResourceNotFoundError as exc:
            raise ProductNotFoundError(
                single_id,
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return self._finalize_sku_detail(detail, single_id)
