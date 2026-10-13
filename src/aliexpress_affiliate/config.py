"""Configuration management for the AliExpress Affiliate API client."""

from __future__ import annotations

import os
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .exceptions import ConfigurationError
from .models.common import Currency, Language

DEFAULT_BASE_URL: str = "https://api-sg.aliexpress.com"
DEFAULT_ENDPOINT_PATH: str = "/sync"


class ClientConfig(BaseModel):
    """Immutable configuration for :class:`AliExpressClient` and :class:`AsyncAliExpressClient`.

    Secrets (:attr:`app_secret`, :attr:`session`, and :attr:`app_signature`) are marked with
    ``repr=False`` so they never leak in ``repr()``, ``str()``, or log output.

    Values can be supplied directly via constructor arguments or loaded automatically
    from environment variables:
    - ``ALIEXPRESS_APP_KEY``
    - ``ALIEXPRESS_APP_SECRET``
    - ``ALIEXPRESS_TRACKING_ID``
    - ``ALIEXPRESS_LANGUAGE`` (default: ``"EN"``)
    - ``ALIEXPRESS_CURRENCY`` (default: ``"USD"``)
    - ``ALIEXPRESS_COUNTRY`` (optional default ``ship_to_country`` / ``country``)
    - ``ALIEXPRESS_APP_SIGNATURE`` (optional legacy ``app_signature`` parameter)
    - ``ALIEXPRESS_SESSION`` (optional TOP session token)
    - ``ALIEXPRESS_BASE_URL`` (default: ``"https://api-sg.aliexpress.com"``)

    Attributes:
        app_key: AliExpress Open Platform application key.
        app_secret: AliExpress Open Platform application secret (excluded from ``repr``).
        tracking_id: Default affiliate tracking ID for link generation and product queries.
        language: Default target language code (e.g., ``Language.EN`` or ``"EN"``).
        currency: Default target currency code (e.g., ``Currency.USD`` or ``"USD"``).
        country: Default destination country code (ISO 3166-1 alpha-2, e.g., ``"US"``).
        app_signature: Optional API signature parameter passed to endpoints that accept it.
        session: Optional TOP session / access token (excluded from ``repr``).
        base_url: Base gateway URL (defaults to ``"https://api-sg.aliexpress.com"``).
        endpoint_path: Gateway REST path (defaults to ``"/sync"``).
        timeout: HTTP request timeout in seconds (defaults to ``30.0``).
        max_retries: Maximum number of automatic retries on transient failures (defaults to ``3``).
        backoff_factor: Exponential backoff multiplier in seconds (defaults to ``0.5``).
        raise_on_empty: If ``True``, raise :class:`ResourceNotFoundError` when list queries return
            0 items. Single-item methods always raise ``*NotFoundError`` when missing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    app_key: str = Field(..., description="AliExpress Open Platform App Key")
    app_secret: str = Field(
        ...,
        repr=False,
        description="AliExpress Open Platform App Secret (redacted in repr)",
    )
    tracking_id: Optional[str] = Field(default=None, description="Default affiliate tracking ID")
    language: str = Field(default=Language.EN.value, description="Default target language")
    currency: str = Field(default=Currency.USD.value, description="Default target currency")
    country: Optional[str] = Field(default=None, description="Default target/ship-to country")
    app_signature: Optional[str] = Field(
        default=None,
        repr=False,
        description="Optional app_signature (redacted in repr)",
    )
    session: Optional[str] = Field(
        default=None,
        repr=False,
        description="Optional session / access_token (redacted in repr)",
    )
    base_url: str = Field(default=DEFAULT_BASE_URL, description="API gateway base URL")
    endpoint_path: str = Field(default=DEFAULT_ENDPOINT_PATH, description="API gateway path")
    timeout: float = Field(default=30.0, gt=0.0, description="HTTP timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Max retries for transient errors")
    backoff_factor: float = Field(default=0.5, ge=0.0, description="Exponential backoff factor")
    raise_on_empty: bool = Field(
        default=False,
        description="Raise ResourceNotFoundError when a list/search query returns zero records",
    )

    @field_validator("app_key", "app_secret")
    @classmethod
    def _validate_non_empty_credentials(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Credential value must not be empty")
        return stripped

    @field_validator("endpoint_path")
    @classmethod
    def _normalize_endpoint_path(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            return DEFAULT_ENDPOINT_PATH
        return stripped if stripped.startswith("/") else f"/{stripped}"

    @classmethod
    def from_env_or_args(
        cls,
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
        endpoint_path: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        raise_on_empty: bool = False,
    ) -> ClientConfig:
        """Create a :class:`ClientConfig` by merging explicit arguments with environment variables.

        Args:
            app_key: Explicit app key, or read from ``ALIEXPRESS_APP_KEY``.
            app_secret: Explicit app secret, or read from ``ALIEXPRESS_APP_SECRET``.
            tracking_id: Explicit tracking ID, or read from ``ALIEXPRESS_TRACKING_ID``.
            language: Explicit language, or read from ``ALIEXPRESS_LANGUAGE`` (defaults to ``"EN"``).
            currency: Explicit currency, or read from ``ALIEXPRESS_CURRENCY`` (defaults to ``"USD"``).
            country: Explicit country code, or read from ``ALIEXPRESS_COUNTRY``.
            app_signature: Explicit app signature, or read from ``ALIEXPRESS_APP_SIGNATURE``.
            session: Explicit session token, or read from ``ALIEXPRESS_SESSION``.
            base_url: Explicit base URL, or read from ``ALIEXPRESS_BASE_URL``.
            endpoint_path: Explicit gateway path (defaults to ``"/sync"``).
            timeout: HTTP request timeout in seconds.
            max_retries: Maximum retry attempts on transient errors.
            backoff_factor: Backoff factor in seconds between retries.
            raise_on_empty: Whether to raise :class:`ResourceNotFoundError` on empty list results.

        Returns:
            Validated :class:`ClientConfig` instance.

        Raises:
            ConfigurationError: If ``app_key`` or ``app_secret`` is missing or invalid.
        """
        resolved_key = app_key if app_key is not None else os.getenv("ALIEXPRESS_APP_KEY")
        resolved_secret = (
            app_secret if app_secret is not None else os.getenv("ALIEXPRESS_APP_SECRET")
        )

        if not resolved_key or not resolved_key.strip():
            raise ConfigurationError(
                "Missing 'app_key'. Provide it via constructor argument or the "
                "ALIEXPRESS_APP_KEY environment variable."
            )
        if not resolved_secret or not resolved_secret.strip():
            raise ConfigurationError(
                "Missing 'app_secret'. Provide it via constructor argument or the "
                "ALIEXPRESS_APP_SECRET environment variable."
            )

        resolved_tracking = (
            tracking_id if tracking_id is not None else os.getenv("ALIEXPRESS_TRACKING_ID")
        )
        raw_lang = language if language is not None else os.getenv("ALIEXPRESS_LANGUAGE", "EN")
        raw_curr = currency if currency is not None else os.getenv("ALIEXPRESS_CURRENCY", "USD")
        resolved_country = country if country is not None else os.getenv("ALIEXPRESS_COUNTRY")
        resolved_sig = (
            app_signature if app_signature is not None else os.getenv("ALIEXPRESS_APP_SIGNATURE")
        )
        resolved_session = session if session is not None else os.getenv("ALIEXPRESS_SESSION")
        resolved_base_url = (
            base_url if base_url is not None else os.getenv("ALIEXPRESS_BASE_URL", DEFAULT_BASE_URL)
        )
        resolved_endpoint = endpoint_path if endpoint_path is not None else DEFAULT_ENDPOINT_PATH

        lang_str = raw_lang.value if isinstance(raw_lang, Language) else str(raw_lang).strip()
        curr_str = raw_curr.value if isinstance(raw_curr, Currency) else str(raw_curr).strip()

        try:
            return cls(
                app_key=resolved_key,
                app_secret=resolved_secret,
                tracking_id=resolved_tracking,
                language=lang_str,
                currency=curr_str,
                country=resolved_country.strip() if resolved_country else None,
                app_signature=resolved_sig,
                session=resolved_session,
                base_url=resolved_base_url.rstrip("/"),
                endpoint_path=resolved_endpoint,
                timeout=timeout,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                raise_on_empty=raise_on_empty,
            )
        except Exception as exc:
            raise ConfigurationError(f"Invalid client configuration: {exc}") from exc
