"""Custom exception hierarchy and automatic API error mapping for AliExpress Affiliate API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional, Union


class AliExpressError(Exception):
    """Base exception for all errors raised by ``aliexpress_affiliate``.

    Args:
        message: Human-readable error message.
        code: Primary TOP/API error code (if returned by AliExpress).
        sub_code: Detailed sub-error code (if returned by AliExpress).
        sub_msg: Detailed sub-error message (if returned by AliExpress).
        request_id: AliExpress request trace identifier.
        raw_response: Parsed JSON response dictionary that triggered the error.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        sub_code: Optional[str] = None,
        sub_msg: Optional[str] = None,
        request_id: Optional[str] = None,
        raw_response: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.reason: str = message  # Backwards compatibility with python-aliexpress-api
        self.code: Optional[str] = code
        self.sub_code: Optional[str] = sub_code
        self.sub_msg: Optional[str] = sub_msg
        self.request_id: Optional[str] = request_id
        self.raw_response: Optional[Mapping[str, Any]] = raw_response

    def __str__(self) -> str:
        parts: list[str] = [self.message]
        details: list[str] = []
        if self.code is not None:
            details.append(f"code={self.code}")
        if self.sub_code is not None:
            details.append(f"sub_code={self.sub_code}")
        if self.sub_msg is not None:
            details.append(f"sub_msg={self.sub_msg}")
        if self.request_id is not None:
            details.append(f"request_id={self.request_id}")
        if details:
            parts.append(f"({', '.join(details)})")
        return " ".join(parts)


class ConfigurationError(AliExpressError):
    """Raised when client configuration (such as ``app_key`` or ``app_secret``) is missing or invalid."""


class ValidationError(AliExpressError):
    """Raised when method arguments, tracking IDs, or product/order IDs are invalid."""


class NetworkError(AliExpressError):
    """Raised when an HTTP transport error, connection failure, timeout, or non-200 status occurs.

    Args:
        message: Description of the network or HTTP transport failure.
        status_code: HTTP status code if a response was received.
        response_text: Raw response body text if available.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code: Optional[int] = status_code
        self.response_text: Optional[str] = response_text


class APIError(AliExpressError):
    """Raised when the AliExpress API returns a gateway or business-level error response."""


class AuthenticationError(APIError):
    """Raised when ``app_key``, ``session`` / ``access_token``, or API permissions are rejected."""


class SignatureError(AuthenticationError):
    """Raised when the request signature (``sign``) or ``app_signature`` is invalid."""


class RateLimitError(APIError):
    """Raised when the AliExpress API rate limit, QPS quota, or call frequency limit is exceeded."""


class ResourceNotFoundError(APIError):
    """Raised when a requested resource is not found or a query returns zero records."""


class ProductNotFoundError(ResourceNotFoundError):
    """Raised when a single product lookup returns no matching product.

    Args:
        product_id: Identifier of the product that was not found.
        message: Optional custom error message.
        code: Optional API error code.
        request_id: Optional request trace ID.
        raw_response: Optional raw API response dictionary.
    """

    def __init__(
        self,
        product_id: Optional[Union[str, int]] = None,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        sub_code: Optional[str] = None,
        sub_msg: Optional[str] = None,
        request_id: Optional[str] = None,
        raw_response: Optional[Mapping[str, Any]] = None,
    ) -> None:
        pid_str = str(product_id) if product_id is not None else None
        resolved_msg = message or (
            f"Product not found for product_id={pid_str!r}"
            if pid_str is not None
            else "Product not found"
        )
        super().__init__(
            resolved_msg,
            code=code,
            sub_code=sub_code,
            sub_msg=sub_msg,
            request_id=request_id,
            raw_response=raw_response,
        )
        self.product_id: Optional[str] = pid_str


class OrderNotFoundError(ResourceNotFoundError):
    """Raised when a single order lookup returns no matching order.

    Args:
        order_id: Identifier of the order that was not found.
        message: Optional custom error message.
        code: Optional API error code.
        request_id: Optional request trace ID.
        raw_response: Optional raw API response dictionary.
    """

    def __init__(
        self,
        order_id: Optional[Union[str, int]] = None,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        sub_code: Optional[str] = None,
        sub_msg: Optional[str] = None,
        request_id: Optional[str] = None,
        raw_response: Optional[Mapping[str, Any]] = None,
    ) -> None:
        oid_str = str(order_id) if order_id is not None else None
        resolved_msg = message or (
            f"Order not found for order_id={oid_str!r}"
            if oid_str is not None
            else "Order not found"
        )
        super().__init__(
            resolved_msg,
            code=code,
            sub_code=sub_code,
            sub_msg=sub_msg,
            request_id=request_id,
            raw_response=raw_response,
        )
        self.order_id: Optional[str] = oid_str


class CategoryNotFoundError(ResourceNotFoundError):
    """Raised when a requested category ID does not exist."""

    def __init__(
        self,
        category_id: Optional[Union[str, int]] = None,
        message: Optional[str] = None,
    ) -> None:
        cid_str = str(category_id) if category_id is not None else None
        resolved_msg = message or (
            f"Category not found for category_id={cid_str!r}"
            if cid_str is not None
            else "Category not found"
        )
        super().__init__(resolved_msg)
        self.category_id: Optional[str] = cid_str


class LinkGenerationError(APIError):
    """Raised when affiliate promotion link generation fails for a requested URL."""

    def __init__(
        self,
        source_value: Optional[str] = None,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
        raw_response: Optional[Mapping[str, Any]] = None,
    ) -> None:
        resolved_msg = message or (
            f"Failed to generate affiliate link for {source_value!r}"
            if source_value is not None
            else "Failed to generate affiliate link"
        )
        super().__init__(
            resolved_msg,
            code=code,
            request_id=request_id,
            raw_response=raw_response,
        )
        self.source_value: Optional[str] = source_value


# Backwards-compatible aliases matching sergioteula/python-aliexpress-api
AliexpressException = AliExpressError
InvalidArgumentException = ValidationError
ProductIdNotFoundException = ValidationError
InvalidTrackingIdException = ValidationError
ApiRequestException = NetworkError
ApiRequestResponseException = APIError
ProductsNotFoundException = ProductNotFoundError
ProductsNotFoudException = ProductNotFoundError
CategoriesNotFoundException = CategoryNotFoundError
CategoriesNotFoudException = CategoryNotFoundError
OrdersNotFoundException = OrderNotFoundError


_SIGNATURE_ERROR_CODES: frozenset[str] = frozenset(
    {"15", "25", "IncompleteSignature", "InvalidSignature"}
)
_AUTH_ERROR_CODES: frozenset[str] = frozenset(
    {
        "11",
        "12",
        "21",
        "22",
        "24",
        "26",
        "27",
        "28",
        "29",
        "41",
        "42",
        "43",
        "401",
        "403",
        "InvalidAppKey",
        "InvalidAccessToken",
    }
)
_RATE_LIMIT_ERROR_CODES: frozenset[str] = frozenset({"7", "40", "50", "429", "ApiCallLimit"})
_NOT_FOUND_BUSINESS_CODES: frozenset[str] = frozenset({"404", "405", "ERROR-404", "ERROR-405"})


def raise_for_top_error(payload: Mapping[str, Any]) -> None:
    """Inspect a raw AliExpress TOP JSON payload for ``error_response`` and raise a typed exception.

    Args:
        payload: Parsed JSON dictionary returned by the AliExpress gateway.

    Raises:
        SignatureError: If the gateway indicates an invalid signature.
        AuthenticationError: If the gateway indicates invalid credentials or permissions.
        RateLimitError: If the gateway indicates rate limiting or quota exhaustion.
        ResourceNotFoundError: If the gateway sub-error indicates an empty or missing resource
            (e.g. ``code="15"`` with ``sub_code="405"`` or ``sub_code="ERROR-405"``).
        APIError: For any other gateway-level ``error_response``.
    """
    error_obj = payload.get("error_response")
    if not isinstance(error_obj, Mapping):
        return

    code = str(error_obj.get("code", "")) if error_obj.get("code") is not None else None
    sub_code = str(error_obj.get("sub_code", "")) if error_obj.get("sub_code") is not None else None
    sub_msg = str(error_obj.get("sub_msg", "")) if error_obj.get("sub_msg") is not None else None
    raw_msg = error_obj.get("msg")
    msg = (
        str(raw_msg)
        if raw_msg is not None and str(raw_msg).strip()
        else (sub_msg or "AliExpress API gateway error")
    )
    request_id = (
        str(error_obj.get("request_id") or payload.get("request_id"))
        if (error_obj.get("request_id") or payload.get("request_id")) is not None
        else None
    )

    combined_text = f"{code or ''} {msg} {sub_code or ''} {sub_msg or ''}".lower()

    exc_cls: type[APIError] = APIError
    if (
        (code in _SIGNATURE_ERROR_CODES and ("sign" in combined_text or code != "15"))
        or code == "25"
        or "signature" in combined_text
        or "sign_error" in combined_text
        or (sub_code is not None and "sign" in sub_code.lower())
    ):
        exc_cls = SignatureError
    elif (
        code in _RATE_LIMIT_ERROR_CODES
        or "apicalllimit" in combined_text
        or "accesscontrol" in combined_text
        or "frequency" in combined_text
        or "rate limit" in combined_text
        or "call limited" in combined_text
        or "quota" in combined_text
        or "qps" in combined_text
    ):
        exc_cls = RateLimitError
    elif (
        code in _AUTH_ERROR_CODES
        or "appkey" in combined_text
        or "app_key" in combined_text
        or "app key" in combined_text
        or "session" in combined_text
        or "token" in combined_text
        or "permission" in combined_text
        or "insufficient isv" in combined_text
        or "unauthorized" in combined_text
    ):
        exc_cls = AuthenticationError
    elif (
        (sub_code is not None and sub_code.upper() in _NOT_FOUND_BUSINESS_CODES)
        or "result is empty" in combined_text
        or "no query results" in combined_text
        or "not found" in combined_text
    ):
        exc_cls = ResourceNotFoundError

    raise exc_cls(
        msg,
        code=code,
        sub_code=sub_code,
        sub_msg=sub_msg,
        request_id=request_id,
        raw_response=payload,
    )


def raise_for_business_error(
    code: Optional[str],
    message: Optional[str],
    *,
    request_id: Optional[str] = None,
    raw_response: Optional[Mapping[str, Any]] = None,
) -> None:
    """Inspect a business-level ``resp_code`` / ``code`` and raise a typed exception if non-200.

    Args:
        code: Business response status code (e.g., ``"200"`` or ``"405"``).
        message: Business response status description (e.g., ``"success"``).
        request_id: AliExpress request trace identifier.
        raw_response: Full parsed JSON response dictionary.

    Raises:
        SignatureError: If the business error indicates an invalid signature.
        AuthenticationError: If the business error indicates authentication failure.
        RateLimitError: If the business error indicates rate limiting.
        ResourceNotFoundError: If the business error code indicates no matching records
            (e.g. ``404``, ``405``, or ``"The result is empty"``).
        APIError: For any other non-200 business error code.
    """
    if code is None or str(code) in ("200", "0"):
        return

    code_str = str(code)
    msg_str = message or f"Business API error {code_str}"
    combined = f"{code_str} {msg_str}".lower()

    exc_cls: type[APIError] = APIError
    if "sign" in combined:
        exc_cls = SignatureError
    elif "rate" in combined or "limit" in combined or "frequency" in combined or code_str == "429":
        exc_cls = RateLimitError
    elif (
        code_str in ("401", "403")
        or "auth" in combined
        or "token" in combined
        or "appkey" in combined
        or "permission" in combined
    ):
        exc_cls = AuthenticationError
    elif (
        code_str.upper() in _NOT_FOUND_BUSINESS_CODES
        or "result is empty" in combined
        or "no query results" in combined
        or "not found" in combined
    ):
        exc_cls = ResourceNotFoundError

    raise exc_cls(
        msg_str,
        code=code_str,
        request_id=request_id,
        raw_response=raw_response,
    )
