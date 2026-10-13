"""Links resource (``aliexpress.affiliate.link.generate``)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Union

from ..exceptions import LinkGenerationError, ResourceNotFoundError, ValidationError
from ..models.common import LinkType
from ..models.links import AffiliateLink, AffiliateLinksResponse, GenerateAffiliateLinksRequest
from ..utils import format_csv_param
from .base import AsyncResource, SyncResource

__all__ = [
    "API_LINK_GENERATE",
    "AsyncLinksResource",
    "LinksResource",
]

API_LINK_GENERATE: str = "aliexpress.affiliate.link.generate"
_MAX_URLS_PER_CALL = 50


def _validate_single_url(source_value: str) -> str:
    """Validate that ``source_value`` is a single non-empty URL string (not a list or CSV)."""
    if not isinstance(source_value, str):
        raise ValidationError(
            f"Expected a single URL string for 'source_value', got {type(source_value).__name__}. "
            "Use 'get_affiliate_links' for batch link generation."
        )
    stripped = source_value.strip()
    if not stripped:
        raise ValidationError("Parameter 'source_value' must not be empty")
    if "," in stripped:
        raise ValidationError(
            f"Expected a single URL for 'source_value', but got comma-separated URLs: {source_value!r}. "
            "Use 'get_affiliate_links' for batch link generation."
        )
    return stripped


class _LinksMixin:
    """Shared request builder and response unwrappers for ``aliexpress.affiliate.link.generate``."""

    def _build_link_request(
        self,
        source_values: Union[str, Sequence[str]],
        *,
        promotion_link_type: Union[LinkType, int] = LinkType.NORMAL,
        tracking_id: str,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> GenerateAffiliateLinksRequest:
        csv_urls = format_csv_param(source_values)
        if not csv_urls or not csv_urls.strip():
            raise ValidationError("Parameter 'source_values' must contain at least one URL")

        parts = [p.strip() for p in csv_urls.split(",") if p.strip()]
        if not parts:
            raise ValidationError("Parameter 'source_values' must contain at least one URL")
        if len(parts) > _MAX_URLS_PER_CALL:
            raise ValidationError(
                f"AliExpress supports at most {_MAX_URLS_PER_CALL} URLs per call, got {len(parts)}"
            )

        return GenerateAffiliateLinksRequest(
            promotion_link_type=int(promotion_link_type),
            source_values=",".join(parts),
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )

    @staticmethod
    def _attach_tracking_id(
        links: list[AffiliateLink],
        tracking_id: Optional[str],
    ) -> list[AffiliateLink]:
        if not tracking_id:
            return links
        return [
            item
            if item.tracking_id is not None
            else item.model_copy(update={"tracking_id": tracking_id})
            for item in links
        ]

    @classmethod
    def _unwrap_single_link(
        cls,
        envelope: AffiliateLinksResponse,
        single_url: str,
        *,
        fallback_tracking_id: Optional[str] = None,
    ) -> AffiliateLink:
        links = cls._attach_tracking_id(
            envelope.promotion_links, envelope.tracking_id or fallback_tracking_id
        )
        if not links:
            raise LinkGenerationError(single_url)
        link = links[0]
        if not link.promotion_link:
            raise LinkGenerationError(
                single_url,
                message=link.message
                or f"No promotion link returned for source_value={single_url!r}",
            )
        return link

    @staticmethod
    def _empty_batch_links(*, raise_on_empty: bool) -> list[AffiliateLink]:
        if raise_on_empty:
            raise
        return []

    @classmethod
    def _unwrap_batch_links(
        cls,
        envelope: AffiliateLinksResponse,
        *,
        raise_on_empty: bool,
        fallback_tracking_id: Optional[str] = None,
    ) -> list[AffiliateLink]:
        links = cls._attach_tracking_id(
            envelope.promotion_links, envelope.tracking_id or fallback_tracking_id
        )
        if raise_on_empty and not links:
            raise ResourceNotFoundError("No affiliate links generated for the given source_values")
        return links


class LinksResource(SyncResource, _LinksMixin):
    """Synchronous resource for ``aliexpress.affiliate.link.generate``."""

    def generate_one(
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
            source_value: Single product or page URL string to convert.
            promotion_link_type: ``LinkType.NORMAL`` (``0``) or ``LinkType.HOTLINK`` (``2``).
            tracking_id: Affiliate tracking ID (defaults to client's ``tracking_id``).
            ship_to_country: Optional destination country code for localized short links.
            app_signature: Optional API signature parameter.

        Returns:
            Single :class:`AffiliateLink` domain model.

        Raises:
            ValidationError: If ``source_value`` is empty, comma-separated, or ``tracking_id`` is missing.
            LinkGenerationError: If the API returns no promotion link for ``source_value``.
            APIError: If the AliExpress API returns a gateway or business error.

        Example:
            ```python
            link = client.links.generate_one("https://www.aliexpress.com/item/33006951782.html")
            print(link.promotion_link)
            ```
        """
        single_url = _validate_single_url(source_value)
        resolved_tracking = self._resolve_tracking_id(tracking_id, required=True)
        assert resolved_tracking is not None

        req = self._build_link_request(
            [single_url],
            promotion_link_type=promotion_link_type,
            tracking_id=resolved_tracking,
            ship_to_country=self._resolve_country(ship_to_country),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_LINK_GENERATE, req.to_api_params(), AffiliateLinksResponse
            )
        except ResourceNotFoundError as exc:
            raise LinkGenerationError(
                single_url,
                message=exc.message,
                code=exc.code,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return self._unwrap_single_link(
            envelope, single_url, fallback_tracking_id=resolved_tracking
        )

    def generate(
        self,
        source_values: Union[str, Sequence[str]],
        *,
        promotion_link_type: Union[LinkType, int] = LinkType.NORMAL,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> list[AffiliateLink]:
        """Batch generate affiliate promotion links for one or more URLs (``aliexpress.affiliate.link.generate``).

        Args:
            source_values: Single URL string, comma-separated URLs, or a sequence of URLs
                (up to 50 URLs per call).
            promotion_link_type: ``LinkType.NORMAL`` (``0``) or ``LinkType.HOTLINK`` (``2``).
            tracking_id: Affiliate tracking ID (defaults to client's ``tracking_id``).
            ship_to_country: Optional destination country code for localized short links.
            app_signature: Optional API signature parameter.

        Returns:
            List of :class:`AffiliateLink` items.

        Raises:
            ValidationError: If ``tracking_id`` is missing or more than 50 URLs are passed.
            ResourceNotFoundError: If ``raise_on_empty=True`` and no links are returned.
            APIError: If the AliExpress API returns a gateway or business error.

        Example:
            ```python
            links = client.links.generate(
                ["https://www.aliexpress.com/item/33006951782.html"],
                promotion_link_type=LinkType.NORMAL,
            )
            print(links[0].promotion_link)
            ```
        """
        resolved_tracking = self._resolve_tracking_id(tracking_id, required=True)
        assert resolved_tracking is not None

        req = self._build_link_request(
            source_values,
            promotion_link_type=promotion_link_type,
            tracking_id=resolved_tracking,
            ship_to_country=self._resolve_country(ship_to_country),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_LINK_GENERATE, req.to_api_params(), AffiliateLinksResponse
            )
        except ResourceNotFoundError:
            return self._empty_batch_links(raise_on_empty=self.config.raise_on_empty)
        return self._unwrap_batch_links(
            envelope,
            raise_on_empty=self.config.raise_on_empty,
            fallback_tracking_id=resolved_tracking,
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
        """Batch generate affiliate promotion links (alias for :meth:`generate`).

        Args:
            links: URL or sequence of URLs to convert.
            link_type: ``LinkType.NORMAL`` (``0``) or ``LinkType.HOTLINK`` (``2``).
            tracking_id: Optional tracking ID override.
            ship_to_country: Optional destination country override.
            app_signature: Optional API signature override.

        Returns:
            List of :class:`AffiliateLink` models.

        Example:
            ```python
            promo_links = client.links.get_affiliate_links(
                ["https://www.aliexpress.com/item/33006951782.html"]
            )
            print(promo_links[0].promotion_link)
            ```
        """
        return self.generate(
            links,
            promotion_link_type=link_type,
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )


class AsyncLinksResource(AsyncResource, _LinksMixin):
    """Asynchronous resource for ``aliexpress.affiliate.link.generate``."""

    async def generate_one(
        self,
        source_value: str,
        *,
        promotion_link_type: Union[LinkType, int] = LinkType.NORMAL,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> AffiliateLink:
        """Asynchronously generate a single affiliate promotion link for one URL.

        Args:
            source_value: Single product or page URL string to convert.
            promotion_link_type: ``LinkType.NORMAL`` (``0``) or ``LinkType.HOTLINK`` (``2``).
            tracking_id: Affiliate tracking ID (defaults to client's ``tracking_id``).
            ship_to_country: Optional destination country code for localized short links.
            app_signature: Optional API signature parameter.

        Returns:
            Single :class:`AffiliateLink` domain model.

        Raises:
            ValidationError: If ``source_value`` is empty, comma-separated, or ``tracking_id`` is missing.
            LinkGenerationError: If the API returns no promotion link for ``source_value``.

        Example:
            ```python
            link = await async_client.links.generate_one(
                "https://www.aliexpress.com/item/33006951782.html"
            )
            print(link.promotion_link)
            ```
        """
        single_url = _validate_single_url(source_value)
        resolved_tracking = self._resolve_tracking_id(tracking_id, required=True)
        assert resolved_tracking is not None

        req = self._build_link_request(
            [single_url],
            promotion_link_type=promotion_link_type,
            tracking_id=resolved_tracking,
            ship_to_country=self._resolve_country(ship_to_country),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_LINK_GENERATE, req.to_api_params(), AffiliateLinksResponse
            )
        except ResourceNotFoundError as exc:
            raise LinkGenerationError(
                single_url,
                message=exc.message,
                code=exc.code,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return self._unwrap_single_link(
            envelope, single_url, fallback_tracking_id=resolved_tracking
        )

    async def generate(
        self,
        source_values: Union[str, Sequence[str]],
        *,
        promotion_link_type: Union[LinkType, int] = LinkType.NORMAL,
        tracking_id: Optional[str] = None,
        ship_to_country: Optional[str] = None,
        app_signature: Optional[str] = None,
    ) -> list[AffiliateLink]:
        """Asynchronously batch generate affiliate promotion links for one or more URLs.

        Args:
            source_values: Single URL string, comma-separated URLs, or sequence of URLs.
            promotion_link_type: ``LinkType.NORMAL`` (``0``) or ``LinkType.HOTLINK`` (``2``).
            tracking_id: Affiliate tracking ID (defaults to client's ``tracking_id``).
            ship_to_country: Optional destination country code.
            app_signature: Optional API signature parameter.

        Returns:
            List of :class:`AffiliateLink` items.

        Example:
            ```python
            links = await async_client.links.generate(
                ["https://www.aliexpress.com/item/33006951782.html"]
            )
            print(links[0].promotion_link)
            ```
        """
        resolved_tracking = self._resolve_tracking_id(tracking_id, required=True)
        assert resolved_tracking is not None

        req = self._build_link_request(
            source_values,
            promotion_link_type=promotion_link_type,
            tracking_id=resolved_tracking,
            ship_to_country=self._resolve_country(ship_to_country),
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_LINK_GENERATE, req.to_api_params(), AffiliateLinksResponse
            )
        except ResourceNotFoundError:
            return self._empty_batch_links(raise_on_empty=self.config.raise_on_empty)
        return self._unwrap_batch_links(
            envelope,
            raise_on_empty=self.config.raise_on_empty,
            fallback_tracking_id=resolved_tracking,
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
        """Asynchronously batch generate affiliate promotion links (alias for :meth:`generate`)."""
        return await self.generate(
            links,
            promotion_link_type=link_type,
            tracking_id=tracking_id,
            ship_to_country=ship_to_country,
            app_signature=app_signature,
        )
