"""Tests verifying exact compatibility with sergioteula/python-aliexpress-api signing logic."""

from __future__ import annotations

import hashlib

from aliexpress_affiliate.signing import (
    SYSTEM_GENERATE_VERSION,
    build_signed_request_params,
    clean_application_parameters,
    generate_timestamp,
    sign,
)


def _reference_sign(secret: str, parameters: dict[str, object] | str) -> str:
    """Exact copy of ``sign(secret, parameters)`` from ``python-aliexpress-api/aliexpress_api/skd/api/base.py``."""
    if isinstance(parameters, dict):
        keys = list(parameters.keys())
        keys.sort()
        canonical = "%s%s%s" % (
            secret,
            "".join("%s%s" % (key, parameters[key]) for key in keys),
            secret,
        )
    else:
        canonical = parameters
    encoded = canonical.encode("utf-8")
    return hashlib.md5(encoded).hexdigest().upper()


def test_sign_matches_reference_implementation_for_dict() -> None:
    secret = "my_top_app_secret_987"
    params: dict[str, object] = {
        "format": "json",
        "app_key": "12345678",
        "sign_method": "md5",
        "v": "2.0",
        "timestamp": "1700000000120",
        "partner_id": SYSTEM_GENERATE_VERSION,
        "method": "aliexpress.affiliate.link.generate",
        "promotion_link_type": 0,
        "source_values": "https://www.aliexpress.com/item/33006951782.html",
        "tracking_id": "default",
    }
    assert sign(secret, params) == _reference_sign(secret, params)
    assert len(sign(secret, params)) == 32
    assert sign(secret, params).isupper()


def test_sign_matches_reference_implementation_for_raw_string() -> None:
    secret = "unused_when_raw_string"
    raw = "secretapp_key123methodtestsecret"
    assert sign(secret, raw) == _reference_sign(secret, raw)


def test_generate_timestamp_matches_reference_rounding() -> None:
    sample_epoch = 1700000000.456
    expected = str(int(float("%.2f" % float(sample_epoch)) * 1000))
    assert generate_timestamp(sample_epoch) == expected
    assert generate_timestamp() != ""


def test_clean_application_parameters_drops_none() -> None:
    cleaned = clean_application_parameters({"a": "1", "b": None, "c": 0, "d": False, "e": ""})
    assert cleaned == {"a": "1", "c": 0, "d": False, "e": ""}


def test_build_signed_request_params_includes_session_and_excludes_none() -> None:
    sys_params, app_params = build_signed_request_params(
        app_key="k1",
        app_secret="s1",
        method="aliexpress.affiliate.product.query",
        app_params={"keywords": "phone", "category_ids": None, "page_no": 1},
        session="tok_123",
        timestamp="1700000000000",
    )
    assert sys_params["app_key"] == "k1"
    assert sys_params["method"] == "aliexpress.affiliate.product.query"
    assert sys_params["session"] == "tok_123"
    assert sys_params["timestamp"] == "1700000000000"
    assert "sign" in sys_params
    assert app_params == {"keywords": "phone", "page_no": 1}

    merged: dict[str, object] = {k: v for k, v in sys_params.items() if k != "sign"}
    merged.update(app_params)
    assert sys_params["sign"] == _reference_sign("s1", merged)
