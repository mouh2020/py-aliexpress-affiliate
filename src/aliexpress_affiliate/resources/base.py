"""Base classes and shared request builder helpers for sync and async API resources."""

from __future__ import annotations

from typing import Optional

from .._http import AsyncTransport, SyncTransport
from ..config import ClientConfig
from ..exceptions import ValidationError


class BaseResourceMixin:
    """Shared configuration helpers for synchronous and asynchronous API resource classes."""

    config: ClientConfig

    def _resolve_tracking_id(
        self,
        tracking_id: Optional[str],
        *,
        required: bool = False,
    ) -> Optional[str]:
        """Resolve ``tracking_id`` from explicit argument or client config.

        Args:
            tracking_id: Explicit tracking ID passed to the method.
            required: If ``True``, raise :class:`ValidationError` when no tracking ID is available.

        Returns:
            Resolved tracking ID string or ``None``.

        Raises:
            ValidationError: If ``required=True`` and neither argument nor config has a tracking ID.
        """
        resolved = tracking_id if tracking_id is not None else self.config.tracking_id
        if required and (not resolved or not resolved.strip()):
            raise ValidationError(
                "A tracking_id is required for this operation. Pass 'tracking_id' explicitly "
                "or configure it on the client / ALIEXPRESS_TRACKING_ID environment variable."
            )
        return resolved

    def _resolve_language(self, target_language: Optional[str]) -> str:
        """Resolve ``target_language`` from explicit argument or client config."""
        return target_language if target_language is not None else self.config.language

    def _resolve_currency(self, target_currency: Optional[str]) -> str:
        """Resolve ``target_currency`` from explicit argument or client config."""
        return target_currency if target_currency is not None else self.config.currency

    def _resolve_country(
        self,
        country: Optional[str],
        *,
        required: bool = False,
        param_name: str = "ship_to_country",
    ) -> Optional[str]:
        """Resolve destination country from explicit argument or client config."""
        resolved = country if country is not None else self.config.country
        if required and (not resolved or not resolved.strip()):
            raise ValidationError(
                f"Parameter '{param_name}' is required for this endpoint. Pass it explicitly "
                "or set a default 'country' on the client / ALIEXPRESS_COUNTRY."
            )
        return resolved

    def _resolve_app_signature(self, app_signature: Optional[str]) -> Optional[str]:
        """Resolve ``app_signature`` from explicit argument or client config."""
        return app_signature if app_signature is not None else self.config.app_signature


class SyncResource(BaseResourceMixin):
    """Base class for synchronous API resource namespaces."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport: SyncTransport = transport
        self.config: ClientConfig = transport.config


class AsyncResource(BaseResourceMixin):
    """Base class for asynchronous API resource namespaces."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport: AsyncTransport = transport
        self.config: ClientConfig = transport.config
