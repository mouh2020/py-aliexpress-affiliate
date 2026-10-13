"""Shared pytest fixtures, CLI options for live API testing, and mock JSON payloads."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from aliexpress_affiliate import AliExpressClient, AsyncAliExpressClient, Currency, Language

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "sanitized_live_responses.json"
REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv_for_live_tests() -> None:
    """Populate ``ALIEXPRESS_*`` env vars from ``.env`` if not already set in ``os.environ``.

    Supports both ``ALIEXPRESS_APP_KEY``/``ALIEXPRESS_APP_SECRET``/``ALIEXPRESS_TRACKING_ID``
    and lower-case ``app_key``/``app_secret``/``trackingid`` keys in ``.env``.
    Never prints or logs secret values.
    """
    dotenv_path = REPO_ROOT / ".env"
    if not dotenv_path.is_file():
        return

    parsed: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        parsed[key.strip()] = val.strip().strip("'\"")

    env_mappings = {
        "ALIEXPRESS_APP_KEY": ("ALIEXPRESS_APP_KEY", "app_key"),
        "ALIEXPRESS_APP_SECRET": ("ALIEXPRESS_APP_SECRET", "app_secret"),
        "ALIEXPRESS_TRACKING_ID": ("ALIEXPRESS_TRACKING_ID", "tracking_id", "trackingid"),
    }
    for target_env, candidate_keys in env_mappings.items():
        if not os.environ.get(target_env):
            for candidate in candidate_keys:
                candidate_val = parsed.get(candidate)
                if candidate_val:
                    os.environ[target_env] = candidate_val
                    break

    if not os.environ.get("ALIEXPRESS_TRACKING_ID"):
        os.environ["ALIEXPRESS_TRACKING_ID"] = "default"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the ``--run-live`` flag to opt in to real AliExpress API tests."""
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run @pytest.mark.live tests against the real AliExpress Affiliate API.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip ``@pytest.mark.live`` tests unless ``--run-live`` and credentials are present."""
    run_live = bool(config.getoption("--run-live"))
    if not run_live:
        skip_not_requested = pytest.mark.skip(
            reason="Live API tests are skipped by default; pass --run-live to execute."
        )
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_not_requested)
        return

    _load_dotenv_for_live_tests()
    has_creds = bool(
        os.environ.get("ALIEXPRESS_APP_KEY") and os.environ.get("ALIEXPRESS_APP_SECRET")
    )
    if not has_creds:
        skip_no_creds = pytest.mark.skip(
            reason=(
                "Live API tests require ALIEXPRESS_APP_KEY and ALIEXPRESS_APP_SECRET "
                "environment variables."
            )
        )
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_no_creds)


@pytest.fixture(scope="session")
def sanitized_live_fixtures() -> dict[str, Any]:
    """Load sanitized real AliExpress API response snapshots from disk."""
    raw = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


@pytest.fixture
def sync_client() -> AliExpressClient:
    """Return a configured synchronous :class:`AliExpressClient` for unit testing."""
    return AliExpressClient(
        app_key="test_app_key",
        app_secret="test_app_secret",
        tracking_id="test_tracking_id",
        language=Language.EN,
        currency=Currency.USD,
        country="US",
        max_retries=2,
        backoff_factor=0.01,
    )


@pytest.fixture
def async_client() -> AsyncAliExpressClient:
    """Return a configured asynchronous :class:`AsyncAliExpressClient` for unit testing."""
    return AsyncAliExpressClient(
        app_key="test_app_key",
        app_secret="test_app_secret",
        tracking_id="test_tracking_id",
        language=Language.EN,
        currency=Currency.USD,
        country="US",
        max_retries=2,
        backoff_factor=0.01,
    )


SAMPLE_PRODUCT_DICT: dict[str, Any] = {
    "app_sale_price": "20.5",
    "original_price": "100",
    "product_detail_url": "https://www.aliexpress.com/item/33006951782.html",
    "product_small_image_urls": {
        "string": [
            "https://ae01.alicdn.com/kf/img1.jpg",
            "https://ae01.alicdn.com/kf/img2.jpg",
        ]
    },
    "second_level_category_name": "Women's Clothing",
    "target_sale_price": "350",
    "second_level_category_id": "333333",
    "discount": "50%",
    "product_main_image_url": "https://ae01.alicdn.com/kf/main.jpg",
    "ean_code": "988312313",
    "first_level_category_id": "1111111",
    "target_sale_price_currency": "USD",
    "target_app_sale_price_currency": "USD",
    "tax_rate": "0.1",
    "platform_product_type": "ALL",
    "original_price_currency": "USD",
    "shop_url": "https://www.aliexpress.com/store/3255036",
    "target_original_price_currency": "USD",
    "product_id": "33006951782",
    "target_original_price": "380",
    "product_video_url": "https://ae01.alicdn.com/kf/video.mp4",
    "first_level_category_name": "Women's Clothing",
    "promotion_link": "http://s.click.aliexpress.com/e/xxxxx",
    "sku_id": "12000029786932962",
    "evaluate_rate": "89.2%",
    "shop_name": "xx store",
    "sale_price": "15.9",
    "product_title": "Spring Autumn Dress",
    "hot_product_commission_rate": "60%",
    "shop_id": "111111",
    "app_sale_price_currency": "USD",
    "sale_price_currency": "USD",
    "lastest_volume": "300",
    "target_app_sale_price": "330",
    "commission_rate": "3.5%",
    "relevant_market_commission_rate": "10%",
    "ship_to_days": "ship to US in 7 days",
    "promo_code_info": {
        "code_campaigntype": "1",
        "code_availabletime_end": "2026-04-30 23:59:59",
        "code_quantity": "1",
        "code_availabletime_start": "2026-04-01 00:00:00",
        "code_value": "On order over USD 10, get USD 7 off",
        "promo_code": "GMG20207",
        "code_mini_spend": "1",
        "code_promotionurl": "https://s.click.aliexpress.com/e/_xxxxx",
    },
}


SAMPLE_ORDER_DICT: dict[str, Any] = {
    "estimated_finished_commission": "17",
    "product_detail_url": "https://www.aliexpress.com/item/32974866139.html",
    "estimated_paid_commission": "22",
    "product_count": "1",
    "order_number": "111111",
    "is_hot_product": "N",
    "parent_order_number": "22222",
    "product_main_image_url": "https://ae01.alicdn.com/kf/order.jpg",
    "order_status": "Payment Completed",
    "settled_currency": "USD",
    "category_id": "11111",
    "product_id": "22222223333",
    "order_type": "global",
    "tracking_id": "trackingId",
    "created_time": "2026-01-15 00:00:00",
    "finished_time": "2026-01-16 00:00:00",
    "completed_settlement_time": "2026-01-20 00:00:00",
    "paid_time": "2026-01-15 00:05:00",
    "customer_parameters": '{"af":0,"dp":1111}',
    "is_new_buyer": "Y",
    "ship_to_country": "US",
    "sub_order_id": "111111",
    "product_title": "Apple iPhone XS Max",
    "incentive_commission_rate": "3.5%",
    "new_buyer_bonus_commission": "12",
    "estimated_incentive_paid_commission": "22",
    "is_affiliate_product": "N",
    "paid_amount": "1000",
    "effect_detail_status": "FullRefund",
    "estimated_incentive_finished_commission": "17",
    "commission_rate": "3.5%",
    "finished_amount": "1000",
    "order_platform": "affiliate_platform",
    "order_id": "22222",
}
