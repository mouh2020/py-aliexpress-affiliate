"""HTTP transport layer (sync and async) with TOP signing, retries, logging, and error mapping."""

from __future__ import annotations

import asyncio
import logging
import re
import time
import urllib.parse
from collections.abc import Mapping
from typing import Any, Optional, TypeVar

import httpx
from pydantic import BaseModel

from .config import ClientConfig
from .exceptions import (
    APIError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    raise_for_business_error,
    raise_for_top_error,
)
from .signing import build_signed_request_params

__all__ = [
    "AsyncTransport",
    "SyncTransport",
    "extract_api_result",
    "method_to_response_key",
    "redact_params_for_logging",
]

logger = logging.getLogger("aliexpress_affiliate")

TModel = TypeVar("TModel", bound=BaseModel)

_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})
_SENSITIVE_PARAM_KEYS: frozenset[str] = frozenset(
    {"app_key", "app_secret", "app_signature", "session", "access_token", "sign", "tracking_id"}
)
_QUERY_SECRET_RE = re.compile(
    r"(?i)((?:app_key|app_secret|app_signature|session|access_token|sign|tracking_id)=)([^&\s'\"]+)"
)

_DEFAULT_HEADERS: dict[str, str] = {
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "Cache-Control": "no-cache",
    "Connection": "Keep-Alive",
}


def redact_params_for_logging(params: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``params`` with any sensitive keys masked as ``'***'`` for safe logging."""
    return {k: ("***" if k.lower() in _SENSITIVE_PARAM_KEYS else v) for k, v in params.items()}


def _redact_text(text: str, config: ClientConfig) -> str:
    """Scrub secret values and sensitive query parameters from error/log strings."""
    redacted = _QUERY_SECRET_RE.sub(r"\1***", text)
    for secret_val in (config.app_secret, config.session, config.app_signature):
        if secret_val:
            redacted = redacted.replace(secret_val, "***")
    return redacted


def _is_retryable_top_rate_limit(payload: Mapping[str, Any]) -> bool:
    """Return ``True`` if ``payload`` is a transient TOP ``ApiCallLimit`` gateway response."""
    error_obj = payload.get("error_response")
    if not isinstance(error_obj, Mapping):
        return False
    code = str(error_obj.get("code", "")).strip()
    return code == "ApiCallLimit"


def _compute_backoff_seconds(
    backoff_factor: float,
    attempt: int,
    *,
    is_rate_limit: bool = False,
) -> float:
    """Compute exponential backoff delay in seconds for ``attempt`` (1-indexed)."""
    base_backoff: float = float(backoff_factor * (2 ** (attempt - 1)))
    if is_rate_limit and backoff_factor >= 0.1:
        return max(1.05, base_backoff)
    return base_backoff


def _parse_json_object(method: str, response: httpx.Response) -> dict[str, Any]:
    """Parse ``response`` as a JSON object dictionary or raise :class:`APIError`."""
    try:
        json_data = response.json()
    except ValueError as exc:
        raise APIError(f"Invalid JSON response from AliExpress for {method}: {exc}") from exc

    if not isinstance(json_data, dict):
        raise APIError(f"Expected JSON object from AliExpress for {method}")
    return json_data


def method_to_response_key(method: str) -> str:
    """Convert an AliExpress TOP method name to its outer JSON response envelope key.

    Args:
        method: API method name, e.g. ``"aliexpress.affiliate.link.generate"``.

    Returns:
        Outer JSON response key, e.g. ``"aliexpress_affiliate_link_generate_response"``.

    Example:
        >>> method_to_response_key("aliexpress.affiliate.link.generate")
        'aliexpress_affiliate_link_generate_response'
    """
    return f"{method.replace('.', '_')}_response"


def _check_block_error(
    block: Mapping[str, Any],
    *,
    method: str,
    request_id: Optional[str],
    raw_response: Mapping[str, Any],
) -> None:
    """Inspect a direct-result envelope block for ``code`` / ``success`` failure indicators."""
    code = block.get("code")
    msg = block.get("msg") or block.get("error_msg")
    success = block.get("success")
    if success in (False, "false", "False"):
        raise_for_business_error(
            str(code) if code is not None and str(code) not in ("0", "200") else "ERROR",
            str(msg) if msg is not None else f"Business call failed for {method}",
            request_id=request_id,
            raw_response=raw_response,
        )
    if code is not None and str(code) not in ("0", "200"):
        raise_for_business_error(
            str(code),
            str(msg) if msg is not None else None,
            request_id=request_id,
            raw_response=raw_response,
        )


def extract_api_result(
    payload: Mapping[str, Any],
    method: str,
) -> dict[str, Any]:
    """Extract the inner ``result`` payload from any of the 3 AliExpress response envelopes.

    Handles:
    1. TOP gateway ``error_response`` envelopes.
    2. Standard ``resp_result`` envelopes (both complex wrapped under ``<method>_response``
       and simplified top-level ``resp_result``).
    3. Direct ``result`` envelopes used by ``aliexpress.affiliate.product.sku.detail.get``
       (nested ``result.result``) and ``aliexpress.affiliate.promotion.info.get``.

    Args:
        payload: Parsed JSON dictionary returned by the AliExpress gateway.
        method: AliExpress API method name used for the request.

    Returns:
        Extracted dictionary corresponding to the method's result model.

    Raises:
        SignatureError: On signature verification failures.
        AuthenticationError: On authentication or permission errors.
        RateLimitError: On rate limit or quota errors.
        ResourceNotFoundError: On business not-found error codes.
        APIError: On any other gateway or business error, or malformed response structure.
    """
    raise_for_top_error(payload)

    request_id_raw = payload.get("request_id")
    request_id = str(request_id_raw) if request_id_raw is not None else None

    response_key = method_to_response_key(method)
    outer: Mapping[str, Any] = (
        payload[response_key]
        if response_key in payload and isinstance(payload[response_key], Mapping)
        else payload
    )

    # Envelope Pattern 1: Standard `resp_result` wrapper (13 of 15 AE Affiliate methods)
    if "resp_result" in outer and isinstance(outer["resp_result"], Mapping):
        resp_result = outer["resp_result"]
        resp_code_raw = resp_result.get("resp_code")
        resp_msg_raw = resp_result.get("resp_msg")
        resp_code = str(resp_code_raw) if resp_code_raw is not None else None
        resp_msg = str(resp_msg_raw) if resp_msg_raw is not None else None

        raise_for_business_error(
            resp_code,
            resp_msg,
            request_id=request_id,
            raw_response=payload,
        )

        inner_result = resp_result.get("result")
        if inner_result is None or inner_result == "":
            return {}
        if isinstance(inner_result, Mapping):
            return dict(inner_result)
        raise APIError(
            f"Unexpected 'result' type in 'resp_result' for {method}: {type(inner_result).__name__}",
            request_id=request_id,
            raw_response=payload,
        )

    # Envelope Pattern 2 & 3: Direct `result` wrapper (`product.sku.detail.get` & `promotion.info.get`)
    if "result" in outer and isinstance(outer["result"], Mapping):
        result_block = outer["result"]
        _check_block_error(outer, method=method, request_id=request_id, raw_response=payload)
        _check_block_error(result_block, method=method, request_id=request_id, raw_response=payload)

        if "result" in result_block and isinstance(result_block["result"], Mapping):
            return dict(result_block["result"])
        return dict(result_block)

    raise APIError(
        f"Unrecognized AliExpress API response structure for method '{method}'",
        request_id=request_id,
        raw_response=payload,
    )


def _raise_for_non_200_status(method: str, response: httpx.Response) -> None:
    """Raise a typed exception for non-200 HTTP responses after retry exhaustion."""
    status = response.status_code
    if status == 429:
        raise RateLimitError(
            f"HTTP 429 Too Many Requests for {method}",
            code="429",
        )
    if status in (401, 403):
        raise AuthenticationError(
            f"HTTP {status} authentication/authorization error for {method}",
            code=str(status),
        )
    raise NetworkError(
        f"Invalid HTTP status {status} for {method}",
        status_code=status,
        response_text=response.text,
    )


class SyncTransport:
    """Synchronous HTTP transport wrapping :class:`httpx.Client` with signing and retries."""

    def __init__(
        self,
        config: ClientConfig,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.config: ClientConfig = config
        self._owns_client: bool = http_client is None
        self._client: httpx.Client = (
            http_client
            if http_client is not None
            else httpx.Client(
                base_url=config.base_url,
                timeout=config.timeout,
                headers=_DEFAULT_HEADERS,
            )
        )

    def close(self) -> None:
        """Close the underlying synchronous ``httpx.Client`` if owned by this transport."""
        if self._owns_client:
            self._client.close()

    def request_raw(
        self,
        method: str,
        app_params: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute a signed POST request to the AliExpress gateway and return the raw JSON dict.

        Args:
            method: AliExpress TOP API method name.
            app_params: Optional mapping of application parameters.

        Returns:
            Parsed JSON dictionary from the HTTP response.

        Raises:
            RateLimitError: If HTTP 429 persists after retries.
            AuthenticationError: If HTTP 401/403 is returned.
            NetworkError: If all retry attempts fail due to transport or HTTP status errors.
            APIError: If the response body is not valid JSON.
        """
        sys_params, cleaned_app_params = build_signed_request_params(
            app_key=self.config.app_key,
            app_secret=self.config.app_secret,
            method=method,
            app_params=app_params,
            session=self.config.session,
        )
        encoded_body = urllib.parse.urlencode(cleaned_app_params)
        url = f"{self.config.base_url}{self.config.endpoint_path}"

        last_error: Optional[Exception] = None
        total_attempts = self.config.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "AliExpress sync request: method=%s attempt=%d/%d params=%s",
                        method,
                        attempt,
                        total_attempts,
                        redact_params_for_logging(cleaned_app_params),
                    )
                response = self._client.post(
                    url,
                    params=sys_params,
                    content=encoded_body.encode("utf-8"),
                    headers=_DEFAULT_HEADERS,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                safe_err = _redact_text(str(exc), self.config)
                logger.warning(
                    "Network error calling %s (attempt %d/%d): %s",
                    method,
                    attempt,
                    total_attempts,
                    safe_err,
                )
                if attempt < total_attempts:
                    time.sleep(_compute_backoff_seconds(self.config.backoff_factor, attempt))
                    continue
                raise NetworkError(f"HTTP request failed for {method}: {safe_err}") from exc

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < total_attempts:
                logger.warning(
                    "Retryable HTTP status %d calling %s (attempt %d/%d)",
                    response.status_code,
                    method,
                    attempt,
                    total_attempts,
                )
                time.sleep(_compute_backoff_seconds(self.config.backoff_factor, attempt))
                continue

            if response.status_code != 200:
                _raise_for_non_200_status(method, response)

            json_data = _parse_json_object(method, response)

            if _is_retryable_top_rate_limit(json_data) and attempt < total_attempts:
                sleep_seconds = _compute_backoff_seconds(
                    self.config.backoff_factor, attempt, is_rate_limit=True
                )
                logger.warning(
                    "Gateway ApiCallLimit calling %s (attempt %d/%d); backing off %.2fs",
                    method,
                    attempt,
                    total_attempts,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
                sys_params, cleaned_app_params = build_signed_request_params(
                    app_key=self.config.app_key,
                    app_secret=self.config.app_secret,
                    method=method,
                    app_params=app_params,
                    session=self.config.session,
                )
                continue

            return json_data

        raise NetworkError(f"Request failed after {total_attempts} attempts: {last_error}")

    def request_model(
        self,
        method: str,
        app_params: Optional[Mapping[str, Any]],
        model_cls: type[TModel],
    ) -> TModel:
        """Execute a signed request, unwrap the AliExpress envelope, and validate into ``model_cls``.

        Args:
            method: AliExpress TOP API method name.
            app_params: Optional application parameters dictionary.
            model_cls: Target Pydantic v2 model class.

        Returns:
            Validated instance of ``model_cls``.
        """
        raw_payload = self.request_raw(method, app_params)
        result_dict = extract_api_result(raw_payload, method)
        return model_cls.model_validate(result_dict)


class AsyncTransport:
    """Asynchronous HTTP transport wrapping :class:`httpx.AsyncClient` with signing and retries."""

    def __init__(
        self,
        config: ClientConfig,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.config: ClientConfig = config
        self._owns_client: bool = http_client is None
        self._client: httpx.AsyncClient = (
            http_client
            if http_client is not None
            else httpx.AsyncClient(
                base_url=config.base_url,
                timeout=config.timeout,
                headers=_DEFAULT_HEADERS,
            )
        )

    async def aclose(self) -> None:
        """Close the underlying asynchronous ``httpx.AsyncClient`` if owned by this transport."""
        if self._owns_client:
            await self._client.aclose()

    async def request_raw(
        self,
        method: str,
        app_params: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute an async signed POST request to the AliExpress gateway and return the raw JSON dict.

        Args:
            method: AliExpress TOP API method name.
            app_params: Optional mapping of application parameters.

        Returns:
            Parsed JSON dictionary from the HTTP response.

        Raises:
            RateLimitError: If HTTP 429 persists after retries.
            AuthenticationError: If HTTP 401/403 is returned.
            NetworkError: If all retry attempts fail due to transport or HTTP status errors.
            APIError: If the response body is not valid JSON.
        """
        sys_params, cleaned_app_params = build_signed_request_params(
            app_key=self.config.app_key,
            app_secret=self.config.app_secret,
            method=method,
            app_params=app_params,
            session=self.config.session,
        )
        encoded_body = urllib.parse.urlencode(cleaned_app_params)
        url = f"{self.config.base_url}{self.config.endpoint_path}"

        last_error: Optional[Exception] = None
        total_attempts = self.config.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "AliExpress async request: method=%s attempt=%d/%d params=%s",
                        method,
                        attempt,
                        total_attempts,
                        redact_params_for_logging(cleaned_app_params),
                    )
                response = await self._client.post(
                    url,
                    params=sys_params,
                    content=encoded_body.encode("utf-8"),
                    headers=_DEFAULT_HEADERS,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                safe_err = _redact_text(str(exc), self.config)
                logger.warning(
                    "Async network error calling %s (attempt %d/%d): %s",
                    method,
                    attempt,
                    total_attempts,
                    safe_err,
                )
                if attempt < total_attempts:
                    await asyncio.sleep(
                        _compute_backoff_seconds(self.config.backoff_factor, attempt)
                    )
                    continue
                raise NetworkError(f"HTTP request failed for {method}: {safe_err}") from exc

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < total_attempts:
                logger.warning(
                    "Retryable HTTP status %d calling %s (attempt %d/%d)",
                    response.status_code,
                    method,
                    attempt,
                    total_attempts,
                )
                await asyncio.sleep(_compute_backoff_seconds(self.config.backoff_factor, attempt))
                continue

            if response.status_code != 200:
                _raise_for_non_200_status(method, response)

            json_data = _parse_json_object(method, response)

            if _is_retryable_top_rate_limit(json_data) and attempt < total_attempts:
                sleep_seconds = _compute_backoff_seconds(
                    self.config.backoff_factor, attempt, is_rate_limit=True
                )
                logger.warning(
                    "Async gateway ApiCallLimit calling %s (attempt %d/%d); backing off %.2fs",
                    method,
                    attempt,
                    total_attempts,
                    sleep_seconds,
                )
                await asyncio.sleep(sleep_seconds)
                sys_params, cleaned_app_params = build_signed_request_params(
                    app_key=self.config.app_key,
                    app_secret=self.config.app_secret,
                    method=method,
                    app_params=app_params,
                    session=self.config.session,
                )
                continue

            return json_data

        raise NetworkError(f"Request failed after {total_attempts} attempts: {last_error}")

    async def request_model(
        self,
        method: str,
        app_params: Optional[Mapping[str, Any]],
        model_cls: type[TModel],
    ) -> TModel:
        """Execute an async signed request, unwrap the AliExpress envelope, and validate into ``model_cls``.

        Args:
            method: AliExpress TOP API method name.
            app_params: Optional application parameters dictionary.
            model_cls: Target Pydantic v2 model class.

        Returns:
            Validated instance of ``model_cls``.
        """
        raw_payload = await self.request_raw(method, app_params)
        result_dict = extract_api_result(raw_payload, method)
        return model_cls.model_validate(result_dict)
