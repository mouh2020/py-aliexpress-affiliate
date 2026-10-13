"""Promotions resource (``featuredpromo.get``, ``featuredpromo.products.get``, and ``promotion.info.get``)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Union

from ..exceptions import ProductNotFoundError, ResourceNotFoundError, ValidationError
from ..models.common import Currency, FeaturedPromoSortBy, Language, Page
from ..models.products import Product
from ..models.promotions import (
    FeaturedPromo,
    FeaturedPromoProductsResponse,
    FeaturedPromosResponse,
    GetFeaturedPromoProductsRequest,
    GetFeaturedPromosRequest,
    GetPromotionInfoRequest,
    ProductPromotionResult,
    PromotionInfoResponse,
)
from ..utils import extract_product_id, format_csv_param, normalize_product_ids
from .base import AsyncResource, SyncResource

__all__ = [
    "API_FEATUREDPROMO_GET",
    "API_FEATUREDPROMO_PRODUCTS_GET",
    "API_PROMOTION_INFO_GET",
    "AsyncPromotionsResource",
    "PromotionsResource",
]

API_FEATUREDPROMO_GET: str = "aliexpress.affiliate.featuredpromo.get"
API_FEATUREDPROMO_PRODUCTS_GET: str = "aliexpress.affiliate.featuredpromo.products.get"
API_PROMOTION_INFO_GET: str = "aliexpress.affiliate.promotion.info.get"


class _PromotionsMixin:
    """Shared request builders and response unwrappers for promotions endpoints."""

    def _build_featured_promo_products_request(
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
        target_currency: Optional[str] = None,
        target_language: Optional[str] = None,
        tracking_id: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> GetFeaturedPromoProductsRequest:
        return GetFeaturedPromoProductsRequest(
            app_signature=app_signature,
            category_id=str(category_id) if category_id is not None else None,
            country=country,
            fields=format_csv_param(fields),
            page_no=page_no,
            page_size=page_size,
            promotion_end_time=promotion_end_time,
            promotion_name=promotion_name,
            promotion_start_time=promotion_start_time,
            sort=sort,
            target_currency=target_currency,
            target_language=target_language,
            tracking_id=tracking_id,
        )

    def _build_promotion_info_request(
        self,
        product_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        ship_to_country: str,
        currency: str,
        target_language: str,
    ) -> GetPromotionInfoRequest:
        normalized = normalize_product_ids(product_ids)
        count = len(normalized.split(","))
        if count > 10:
            raise ValidationError(
                f"aliexpress.affiliate.promotion.info.get accepts at most 10 product IDs, got {count}"
            )
        return GetPromotionInfoRequest(
            product_id=normalized,
            ship_to_country=ship_to_country,
            currency=currency,
            target_language=target_language,
        )

    @staticmethod
    def _empty_featured_promos(*, raise_on_empty: bool) -> list[FeaturedPromo]:
        if raise_on_empty:
            raise
        return []

    @staticmethod
    def _finalize_featured_promos(
        envelope: FeaturedPromosResponse,
        *,
        raise_on_empty: bool,
    ) -> list[FeaturedPromo]:
        if raise_on_empty and not envelope.promos:
            raise ResourceNotFoundError("No featured promotions found")
        return envelope.promos

    @staticmethod
    def _empty_featured_promo_products_page(
        page_no: Optional[int],
        page_size: Optional[int],
        *,
        raise_on_empty: bool,
    ) -> Page[Product]:
        if raise_on_empty:
            raise
        return Page[Product](
            items=[],
            page_no=page_no or 1,
            page_size=page_size or 0,
            total_count=0,
            total_pages=0,
        )

    @staticmethod
    def _finalize_featured_promo_products_page(
        envelope: FeaturedPromoProductsResponse,
        *,
        page_no: Optional[int],
        page_size: Optional[int],
        raise_on_empty: bool,
    ) -> Page[Product]:
        if raise_on_empty and not envelope.products:
            raise ResourceNotFoundError("No featured promotion products found")
        return envelope.to_page(requested_page_no=page_no, requested_page_size=page_size)

    @staticmethod
    def _unwrap_single_promotion_info(
        envelope: PromotionInfoResponse,
        single_id: str,
    ) -> ProductPromotionResult:
        if not envelope.promotion_results:
            raise ProductNotFoundError(
                single_id,
                message=f"No promotion information found for product_id={single_id!r}",
            )
        return envelope.promotion_results[0]

    @staticmethod
    def _empty_promotions_info(*, raise_on_empty: bool) -> list[ProductPromotionResult]:
        if raise_on_empty:
            raise
        return []

    @staticmethod
    def _finalize_promotions_info(
        envelope: PromotionInfoResponse,
        *,
        raise_on_empty: bool,
    ) -> list[ProductPromotionResult]:
        if raise_on_empty and not envelope.promotion_results:
            raise ResourceNotFoundError("No promotion info found for the requested product_ids")
        return envelope.promotion_results


class PromotionsResource(SyncResource, _PromotionsMixin):
    """Synchronous resource for ``featuredpromo.get``, ``featuredpromo.products.get``, and ``promotion.info.get``."""

    def get_featured_promos(
        self,
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> list[FeaturedPromo]:
        """Retrieve active featured promotions (``aliexpress.affiliate.featuredpromo.get``).

        Args:
            fields: Optional response field list.
            app_signature: Optional API signature parameter.

        Returns:
            List of :class:`FeaturedPromo` domain models.

        Example:
            ```python
            promos = client.promotions.get_featured_promos()
            for promo in promos:
                print(promo.promo_name, promo.promo_description, promo.product_count)
            ```
        """
        req = GetFeaturedPromosRequest(
            fields=format_csv_param(fields),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_FEATUREDPROMO_GET, req.to_api_params(), FeaturedPromosResponse
            )
        except ResourceNotFoundError:
            return self._empty_featured_promos(raise_on_empty=self.config.raise_on_empty)
        return self._finalize_featured_promos(envelope, raise_on_empty=self.config.raise_on_empty)

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
        """Retrieve affiliate products in a featured promotion (``aliexpress.affiliate.featuredpromo.products.get``).

        Returns:
            Typed :class:`Page[Product]` containing featured promotion products.

        Example:
            ```python
            page = client.promotions.get_featured_promo_products(
                promotion_name="Hot Product",
                sort=FeaturedPromoSortBy.COMMISSION_DESC,
            )
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_featured_promo_products_request(
            promotion_name=promotion_name,
            category_id=category_id,
            promotion_start_time=promotion_start_time,
            promotion_end_time=promotion_end_time,
            page_no=page_no,
            page_size=page_size,
            sort=sort,
            fields=fields,
            country=self._resolve_country(country, param_name="country"),
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_FEATUREDPROMO_PRODUCTS_GET,
                req.to_api_params(),
                FeaturedPromoProductsResponse,
            )
        except ResourceNotFoundError:
            return self._empty_featured_promo_products_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_featured_promo_products_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    def get_promotion_info(
        self,
        product_id: Union[str, int],
        *,
        ship_to_country: Optional[str] = None,
        currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> ProductPromotionResult:
        """Retrieve real-time applicable coupons and promotions for a single product (``aliexpress.affiliate.promotion.info.get``).

        Args:
            product_id: Single product ID (``int`` or ``str``) or AliExpress item URL.
            ship_to_country: Destination country code (defaults to client's ``country``).
            currency: Target ISO 4217 currency code (defaults to client's ``currency``).
            target_language: Target language code (defaults to client's ``language``).

        Returns:
            Single :class:`ProductPromotionResult` domain model for ``product_id``.

        Raises:
            ValidationError: If ``product_id`` is a sequence, comma-separated, or invalid.
            ProductNotFoundError: If the API returns no promotion record for ``product_id``.

        Example:
            ```python
            promo = client.promotions.get_promotion_info("1005006067128597", ship_to_country="US")
            for coupon in promo.promotions:
                print(coupon.redemption_code, coupon.money_off_amount)
            ```
        """
        single_id = extract_product_id(product_id)
        resolved_country = self._resolve_country(
            ship_to_country, required=True, param_name="ship_to_country"
        )
        assert resolved_country is not None
        curr_val = currency.value if isinstance(currency, Currency) else currency
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_promotion_info_request(
            [single_id],
            ship_to_country=resolved_country,
            currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
        )
        try:
            envelope = self._transport.request_model(
                API_PROMOTION_INFO_GET, req.to_api_params(), PromotionInfoResponse
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
        return self._unwrap_single_promotion_info(envelope, single_id)

    def get_promotions_info(
        self,
        product_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        ship_to_country: Optional[str] = None,
        currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> list[ProductPromotionResult]:
        """Batch retrieve real-time applicable coupons and promotions for up to 10 products (``aliexpress.affiliate.promotion.info.get``).

        Args:
            product_ids: Up to 10 product IDs or URLs (single value, comma-separated string, or sequence).
            ship_to_country: Destination country code (defaults to client's ``country``).
            currency: Target ISO 4217 currency code (defaults to client's ``currency``).
            target_language: Target language code (defaults to client's ``language``).

        Returns:
            List of :class:`ProductPromotionResult` domain models.

        Example:
            ```python
            results = client.promotions.get_promotions_info(
                ["1005006067128597", "33006951782"],
                ship_to_country="US",
            )
            ```
        """
        resolved_country = self._resolve_country(
            ship_to_country, required=True, param_name="ship_to_country"
        )
        assert resolved_country is not None
        curr_val = currency.value if isinstance(currency, Currency) else currency
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_promotion_info_request(
            product_ids,
            ship_to_country=resolved_country,
            currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
        )
        try:
            envelope = self._transport.request_model(
                API_PROMOTION_INFO_GET, req.to_api_params(), PromotionInfoResponse
            )
        except ResourceNotFoundError:
            return self._empty_promotions_info(raise_on_empty=self.config.raise_on_empty)
        return self._finalize_promotions_info(envelope, raise_on_empty=self.config.raise_on_empty)


class AsyncPromotionsResource(AsyncResource, _PromotionsMixin):
    """Asynchronous resource for ``featuredpromo.get``, ``featuredpromo.products.get``, and ``promotion.info.get``."""

    async def get_featured_promos(
        self,
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> list[FeaturedPromo]:
        """Asynchronously retrieve active featured promotions (``aliexpress.affiliate.featuredpromo.get``).

        Example:
            ```python
            promos = await async_client.promotions.get_featured_promos()
            ```
        """
        req = GetFeaturedPromosRequest(
            fields=format_csv_param(fields),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_FEATUREDPROMO_GET, req.to_api_params(), FeaturedPromosResponse
            )
        except ResourceNotFoundError:
            return self._empty_featured_promos(raise_on_empty=self.config.raise_on_empty)
        return self._finalize_featured_promos(envelope, raise_on_empty=self.config.raise_on_empty)

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
        """Asynchronously retrieve affiliate products in a featured promotion (``aliexpress.affiliate.featuredpromo.products.get``).

        Example:
            ```python
            page = await async_client.promotions.get_featured_promo_products(
                promotion_name="weeklydeals"
            )
            ```
        """
        curr_val = (
            target_currency.value if isinstance(target_currency, Currency) else target_currency
        )
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_featured_promo_products_request(
            promotion_name=promotion_name,
            category_id=category_id,
            promotion_start_time=promotion_start_time,
            promotion_end_time=promotion_end_time,
            page_no=page_no,
            page_size=page_size,
            sort=sort,
            fields=fields,
            country=self._resolve_country(country, param_name="country"),
            target_currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
            tracking_id=self._resolve_tracking_id(tracking_id),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_FEATUREDPROMO_PRODUCTS_GET,
                req.to_api_params(),
                FeaturedPromoProductsResponse,
            )
        except ResourceNotFoundError:
            return self._empty_featured_promo_products_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_featured_promo_products_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    async def get_promotion_info(
        self,
        product_id: Union[str, int],
        *,
        ship_to_country: Optional[str] = None,
        currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> ProductPromotionResult:
        """Asynchronously retrieve real-time applicable coupons and promotions for a single product.

        Example:
            ```python
            promo = await async_client.promotions.get_promotion_info(
                "1005006067128597",
                ship_to_country="US",
            )
            ```
        """
        single_id = extract_product_id(product_id)
        resolved_country = self._resolve_country(
            ship_to_country, required=True, param_name="ship_to_country"
        )
        assert resolved_country is not None
        curr_val = currency.value if isinstance(currency, Currency) else currency
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_promotion_info_request(
            [single_id],
            ship_to_country=resolved_country,
            currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
        )
        try:
            envelope = await self._transport.request_model(
                API_PROMOTION_INFO_GET, req.to_api_params(), PromotionInfoResponse
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
        return self._unwrap_single_promotion_info(envelope, single_id)

    async def get_promotions_info(
        self,
        product_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        ship_to_country: Optional[str] = None,
        currency: Optional[Union[Currency, str]] = None,
        target_language: Optional[Union[Language, str]] = None,
    ) -> list[ProductPromotionResult]:
        """Asynchronously batch retrieve real-time applicable coupons and promotions for up to 10 products.

        Example:
            ```python
            results = await async_client.promotions.get_promotions_info(
                ["1005006067128597", "33006951782"],
                ship_to_country="US",
            )
            ```
        """
        resolved_country = self._resolve_country(
            ship_to_country, required=True, param_name="ship_to_country"
        )
        assert resolved_country is not None
        curr_val = currency.value if isinstance(currency, Currency) else currency
        lang_val = (
            target_language.value if isinstance(target_language, Language) else target_language
        )
        req = self._build_promotion_info_request(
            product_ids,
            ship_to_country=resolved_country,
            currency=self._resolve_currency(curr_val),
            target_language=self._resolve_language(lang_val),
        )
        try:
            envelope = await self._transport.request_model(
                API_PROMOTION_INFO_GET, req.to_api_params(), PromotionInfoResponse
            )
        except ResourceNotFoundError:
            return self._empty_promotions_info(raise_on_empty=self.config.raise_on_empty)
        return self._finalize_promotions_info(envelope, raise_on_empty=self.config.raise_on_empty)
