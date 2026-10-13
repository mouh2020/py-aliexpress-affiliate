"""Helper utilities for parameter normalization, single-item validation, and ID extraction."""

from __future__ import annotations

import re
from collections.abc import Sequence
from enum import Enum
from typing import Any, Optional, Union

from .exceptions import ValidationError

_DIGITS_ONLY_RE = re.compile(r"^[0-9]+$")
# Negative lookbehind (?<!/) prevents matching numeric subdomains right after "https://"
_URL_PRODUCT_ID_RE = re.compile(r"(?<!/)(/)([0-9]+)(\.)")


def extract_product_id(value: Union[str, int]) -> str:
    """Extract a numeric AliExpress product ID from a single raw ID or product URL.

    Preserves the regex extraction behavior of ``aliexpress_api/tools/get_product_id.py``
    from ``sergioteula/python-aliexpress-api`` while hardening against ``//`` subdomain
    false positives and comma-separated multi-ID strings.

    Args:
        value: A single numeric product ID (e.g. ``"1005004757833857"`` or ``1005004757833857``)
            or an AliExpress item URL (e.g. ``"https://www.aliexpress.com/item/33006951782.html"``).

    Returns:
        The extracted numeric product ID string.

    Raises:
        ValidationError: If ``value`` is not a single valid product ID or URL (for example,
            if a list or comma-separated multiple IDs are passed).

    Example:
        >>> extract_product_id("https://www.aliexpress.com/item/33006951782.html")
        '33006951782'
        >>> extract_product_id(33006951782)
        '33006951782'
    """
    if isinstance(value, int) and not isinstance(value, bool):
        if value <= 0:
            raise ValidationError(f"Product ID must be a positive integer, got {value}")
        return str(value)
    if not isinstance(value, str):
        raise ValidationError(
            f"Product ID must be a single string or int, got {type(value).__name__}"
        )

    stripped = value.strip()
    if not stripped:
        raise ValidationError("Product ID cannot be empty")

    if "," in stripped:
        raise ValidationError(
            f"Expected a single product_id, but got comma-separated values: {value!r}. "
            "Use 'get_products_details' for batch lookups."
        )

    if _DIGITS_ONLY_RE.match(stripped):
        return stripped

    match = _URL_PRODUCT_ID_RE.search(stripped)
    if match and match.group(2):
        return match.group(2)

    raise ValidationError(f"Product id not found: {value}")


def normalize_product_ids(values: Union[str, int, Sequence[Union[str, int]]]) -> str:
    """Normalize one or more product IDs or AliExpress URLs into a comma-separated ID string.

    Args:
        values: A single product ID/URL, a comma-separated string of IDs/URLs, or a sequence
            of product IDs/URLs.

    Returns:
        Comma-separated string of numeric product IDs.

    Raises:
        ValidationError: If ``values`` is empty or contains an invalid product identifier.

    Example:
        >>> normalize_product_ids(["1005001", "https://aliexpress.com/item/1005002.html"])
        '1005001,1005002'
    """
    raw_items: list[Union[str, int]]
    if isinstance(values, int) and not isinstance(values, bool):
        raw_items = [values]
    elif isinstance(values, str):
        raw_items = [part.strip() for part in values.split(",") if part.strip()]
    elif isinstance(values, Sequence):
        raw_items = list(values)
    else:
        raise ValidationError("Argument 'product_ids' must be a string, int, or sequence")

    if not raw_items:
        raise ValidationError("At least one product ID must be provided")

    extracted = [extract_product_id(item) for item in raw_items]
    return ",".join(extracted)


def validate_single_order_id(order_id: Union[str, int]) -> str:
    """Validate and normalize a single order ID (rejecting sequences and comma-separated IDs).

    Args:
        order_id: Single order or sub-order ID as ``int`` or ``str``.

    Returns:
        Normalized numeric order ID string.

    Raises:
        ValidationError: If ``order_id`` is empty, non-numeric, a sequence, or comma-separated.
    """
    if isinstance(order_id, int) and not isinstance(order_id, bool):
        if order_id <= 0:
            raise ValidationError(f"Order ID must be a positive integer, got {order_id}")
        return str(order_id)
    if not isinstance(order_id, str):
        raise ValidationError(
            f"Order ID must be a single string or int, got {type(order_id).__name__}. "
            "Use 'get_orders_details' for batch lookups."
        )

    stripped = order_id.strip()
    if not stripped:
        raise ValidationError("Order ID cannot be empty")
    if "," in stripped:
        raise ValidationError(
            f"Expected a single order_id, but got comma-separated values: {order_id!r}. "
            "Use 'get_orders_details' for batch lookups."
        )
    if not _DIGITS_ONLY_RE.match(stripped):
        raise ValidationError(f"Order ID must be numeric, got {order_id!r}")
    return stripped


def normalize_order_ids(values: Union[str, int, Sequence[Union[str, int]]]) -> str:
    """Normalize one or more order IDs into a comma-separated string of numeric IDs.

    Args:
        values: Single order ID, comma-separated string of order IDs, or sequence of order IDs.

    Returns:
        Comma-separated string of validated numeric order IDs.

    Raises:
        ValidationError: If ``values`` is empty or contains non-numeric order IDs.
    """
    raw_items: list[Union[str, int]]
    if isinstance(values, int) and not isinstance(values, bool):
        raw_items = [values]
    elif isinstance(values, str):
        raw_items = [part.strip() for part in values.split(",") if part.strip()]
    elif isinstance(values, Sequence):
        raw_items = list(values)
    else:
        raise ValidationError("Argument 'order_ids' must be a string, int, or sequence")

    if not raw_items:
        raise ValidationError("Parameter 'order_ids' must contain at least one order ID")

    validated = [validate_single_order_id(item) for item in raw_items]
    return ",".join(validated)


def format_csv_param(
    value: Optional[Union[str, int, Enum, Sequence[Union[str, int, Enum]]]],
) -> Optional[str]:
    """Convert a string, integer, Enum, or sequence of values into a comma-separated string.

    Args:
        value: Optional single value or sequence of values.

    Returns:
        Comma-separated string, or ``None`` if ``value`` is ``None``.

    Raises:
        ValidationError: If ``value`` has an unsupported type.

    Example:
        >>> format_csv_param(["commission_rate", "sale_price"])
        'commission_rate,sale_price'
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, Sequence):
        items: list[str] = []
        for item in value:
            if isinstance(item, Enum):
                items.append(str(item.value))
            elif isinstance(item, (str, int)) and not isinstance(item, bool):
                items.append(str(item))
            else:
                raise ValidationError(
                    f"Unsupported element type in list parameter: {type(item).__name__}"
                )
        return ",".join(items)
    raise ValidationError(f"Argument should be a sequence or string, got: {value!r}")


def unwrap_xml_list(value: Any, *inner_keys: str) -> list[Any]:
    """Unwrap TOP XML-to-JSON list containers such as ``{"product": [...]}`` or ``[...]``.

    AliExpress TOP gateway responses often serialize array fields either directly as a
    JSON list ``[...]`` or wrapped inside an inner dictionary ``{inner_key: [...]}``
    (e.g. ``{"products": {"product": [...]}}`` or
    ``{"ae_item_sku_info": {"traffic_sku_info_list": [...]}}``).
    This helper normalizes all variants into a flat Python ``list``.

    Args:
        value: The raw field value from the JSON response.
        *inner_keys: One or more candidate inner keys used by TOP serialization
            (e.g. ``"traffic_sku_info_list"``, ``"ae_item_sku_info_d_t_o"``).

    Returns:
        Normalized Python list of items.
    """
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in inner_keys:
            if key in value:
                nested = value[key]
                if nested is None or nested == "":
                    return []
                if isinstance(nested, list):
                    return nested
                return [nested]
        if len(value) == 1:
            sole_val = next(iter(value.values()))
            if sole_val is None or sole_val == "":
                return []
            if isinstance(sole_val, list):
                return sole_val
        return []
    return [value]


# Backwards-compatible helper aliases
get_product_id = extract_product_id
get_product_ids = normalize_product_ids
get_list_as_string = format_csv_param
