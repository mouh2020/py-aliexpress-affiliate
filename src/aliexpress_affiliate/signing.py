"""Exact TOP MD5 request-signing logic preserved from sergioteula/python-aliexpress-api.

Attribution:
    Adapted from ``aliexpress_api/skd/api/base.py`` in
    ``https://github.com/sergioteula/python-aliexpress-api`` (MIT License).
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from typing import Any, Optional, Union

SYSTEM_GENERATE_VERSION: str = "taobao-sdk-python-20200924"

P_APPKEY: str = "app_key"
P_API: str = "method"
P_SESSION: str = "session"
P_ACCESS_TOKEN: str = "access_token"
P_VERSION: str = "v"
P_FORMAT: str = "format"
P_TIMESTAMP: str = "timestamp"
P_SIGN: str = "sign"
P_SIGN_METHOD: str = "sign_method"
P_PARTNER_ID: str = "partner_id"

N_REST: str = "/sync"


def generate_timestamp(now: Optional[float] = None) -> str:
    """Generate the millisecond timestamp string exactly as ``RestApi.getResponse`` does.

    In ``python-aliexpress-api/aliexpress_api/skd/api/base.py``:
        ``timestamp_temp = "%.2f" % (float(time.time()))``
        ``timestamp_temp = str(int(float(timestamp_temp) * 1000))``

    Args:
        now: Optional UNIX epoch timestamp in seconds (defaults to ``time.time()``).

    Returns:
        String representation of the millisecond timestamp rounded to 10ms precision.

    Example:
        >>> generate_timestamp(1700000000.123)
        '1700000000120'
    """
    current = float(time.time() if now is None else now)
    timestamp_temp = "%.2f" % current
    return str(int(float(timestamp_temp) * 1000))


def sign(secret: str, parameters: Union[Mapping[str, Any], str]) -> str:
    """Compute the uppercase MD5 signature for AliExpress TOP API requests.

    Preserves the exact signing algorithm from
    ``sergioteula/python-aliexpress-api`` (``aliexpress_api/skd/api/base.py``):

    1. If ``parameters`` is a mapping, sort its keys in ascending ASCII order.
    2. Concatenate ``secret + "".join(f"{k}{parameters[k]}" for k in sorted_keys) + secret``.
    3. Encode the resulting string as UTF-8.
    4. Compute the MD5 hex digest and convert to uppercase.

    Args:
        secret: The AliExpress application secret (``app_secret``).
        parameters: Combined dictionary of system and application parameters, or a
            pre-formatted string.

    Returns:
        32-character uppercase hexadecimal MD5 signature string.

    Example:
        >>> sign("my_secret", {"app_key": "12345", "method": "aliexpress.affiliate.category.get"})
        '66D258EEB5EE0579B502F35CC948085F'
    """
    if isinstance(parameters, Mapping):
        keys = sorted(parameters.keys())
        canonical_str = "%s%s%s" % (
            secret,
            "".join("%s%s" % (key, parameters[key]) for key in keys),
            secret,
        )
    else:
        canonical_str = parameters

    encoded = canonical_str.encode("utf-8")
    return hashlib.md5(encoded).hexdigest().upper()


def clean_application_parameters(raw_params: Mapping[str, Any]) -> dict[str, Any]:
    """Filter out ``None`` values from application parameters before signing and encoding.

    Args:
        raw_params: Raw dictionary of application-level request parameters.

    Returns:
        Dictionary containing only non-``None`` application parameters.
    """
    cleaned: dict[str, Any] = {}
    for key, value in raw_params.items():
        if value is not None:
            cleaned[key] = value
    return cleaned


def build_signed_request_params(
    *,
    app_key: str,
    app_secret: str,
    method: str,
    app_params: Optional[Mapping[str, Any]] = None,
    session: Optional[str] = None,
    timestamp: Optional[str] = None,
    partner_id: str = SYSTEM_GENERATE_VERSION,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Build signed system query parameters and cleaned application body parameters.

    Follows the exact protocol of ``RestApi.getResponse`` in ``base.py``:
    - System parameters (including ``sign``) are sent in the URL query string.
    - Application parameters (excluding ``None``) are included in the MD5 signature
      calculation and sent as ``application/x-www-form-urlencoded`` in the POST body.

    Args:
        app_key: AliExpress application key.
        app_secret: AliExpress application secret.
        method: AliExpress TOP API method name (e.g. ``"aliexpress.affiliate.link.generate"``).
        app_params: Optional mapping of application parameters for the method.
        session: Optional session / access token (mapped to ``session`` system parameter).
        timestamp: Optional explicit timestamp override (useful for deterministic tests).
        partner_id: SDK partner identifier (defaults to ``"taobao-sdk-python-20200924"``).

    Returns:
        A 2-tuple of ``(sys_parameters, application_parameters)``.
    """
    ts = timestamp if timestamp is not None else generate_timestamp()
    sys_parameters: dict[str, str] = {
        P_FORMAT: "json",
        P_APPKEY: app_key,
        P_SIGN_METHOD: "md5",
        P_VERSION: "2.0",
        P_TIMESTAMP: ts,
        P_PARTNER_ID: partner_id,
        P_API: method,
    }
    if session is not None:
        sys_parameters[P_SESSION] = session

    application_parameter = clean_application_parameters(app_params or {})
    sign_parameter: dict[str, Any] = dict(sys_parameters)
    sign_parameter.update(application_parameter)
    sys_parameters[P_SIGN] = sign(app_secret, sign_parameter)

    return sys_parameters, application_parameter
