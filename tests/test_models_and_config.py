"""Tests for ClientConfig, secret redaction, utilities, and Pydantic v2 models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from aliexpress_affiliate import (
    AffiliateLinksResponse,
    CategoriesResponse,
    ClientConfig,
    ConfigurationError,
    Currency,
    CursorPage,
    Language,
    Order,
    OrderListByIndexResponse,
    OrderListResponse,
    Page,
    Product,
    ProductSkuDetail,
    ProductsResponse,
    PromotionInfoResponse,
    ValidationError,
    extract_product_id,
    format_csv_param,
    normalize_order_ids,
    normalize_product_ids,
    validate_single_order_id,
)
from aliexpress_affiliate._http import redact_params_for_logging
from aliexpress_affiliate.models.common import LinkType

from .conftest import SAMPLE_ORDER_DICT, SAMPLE_PRODUCT_DICT


def test_config_from_env_and_secret_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALIEXPRESS_APP_KEY", "env_key")
    monkeypatch.setenv("ALIEXPRESS_APP_SECRET", "super_secret_value_123")
    monkeypatch.setenv("ALIEXPRESS_TRACKING_ID", "env_track")
    monkeypatch.setenv("ALIEXPRESS_LANGUAGE", "FR")
    monkeypatch.setenv("ALIEXPRESS_CURRENCY", "EUR")
    monkeypatch.setenv("ALIEXPRESS_COUNTRY", "FR")
    monkeypatch.setenv("ALIEXPRESS_SESSION", "secret_session_token_999")
    monkeypatch.setenv("ALIEXPRESS_APP_SIGNATURE", "secret_app_sig_888")

    cfg = ClientConfig.from_env_or_args(endpoint_path="sync")
    assert cfg.app_key == "env_key"
    assert cfg.app_secret == "super_secret_value_123"
    assert cfg.tracking_id == "env_track"
    assert cfg.language == "FR"
    assert cfg.currency == "EUR"
    assert cfg.country == "FR"
    assert cfg.endpoint_path == "/sync"

    # Security check: secrets must NEVER appear in repr() or str()
    assert "super_secret_value_123" not in repr(cfg)
    assert "super_secret_value_123" not in str(cfg)
    assert "secret_session_token_999" not in repr(cfg)
    assert "secret_app_sig_888" not in repr(cfg)

    redacted = redact_params_for_logging(
        {
            "keywords": "phone",
            "app_key": "secret_key",
            "tracking_id": "secret_track",
            "app_signature": "secret_sig",
            "session": "secret_tok",
        }
    )
    assert redacted == {
        "keywords": "phone",
        "app_key": "***",
        "tracking_id": "***",
        "app_signature": "***",
        "session": "***",
    }


def test_config_missing_credentials_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALIEXPRESS_APP_KEY", raising=False)
    monkeypatch.delenv("ALIEXPRESS_APP_SECRET", raising=False)

    with pytest.raises(ConfigurationError, match="app_key"):
        ClientConfig.from_env_or_args()

    with pytest.raises(ConfigurationError, match="app_secret"):
        ClientConfig.from_env_or_args(app_key="only_key")

    with pytest.raises(ConfigurationError):
        ClientConfig.from_env_or_args(app_key="k", app_secret="s", timeout=-1.0)


def test_extract_and_normalize_product_and_order_ids() -> None:
    assert extract_product_id(33006951782) == "33006951782"
    assert extract_product_id("33006951782") == "33006951782"
    assert (
        extract_product_id("https://www.aliexpress.com/item/1005004757833857.html?spm=a2g0o")
        == "1005004757833857"
    )
    assert (
        normalize_product_ids(["33006951782", "https://es.aliexpress.com/item/999888777.html"])
        == "33006951782,999888777"
    )
    assert normalize_product_ids("111, 222") == "111,222"
    assert normalize_product_ids(444) == "444"

    # Reject empty, negative, boolean, comma-separated, or numeric subdomain false-positives
    with pytest.raises(ValidationError):
        extract_product_id("")
    with pytest.raises(ValidationError):
        extract_product_id(-5)
    with pytest.raises(ValidationError):
        extract_product_id(True)
    with pytest.raises(ValidationError, match="Expected a single product_id"):
        extract_product_id("111,222")
    with pytest.raises(ValidationError):
        extract_product_id("https://12345.aliexpress.com/store/home")
    with pytest.raises(ValidationError):
        extract_product_id("https://example.com/not-a-product")
    with pytest.raises(ValidationError):
        normalize_product_ids([])

    # Order ID single and batch validation
    assert validate_single_order_id(22222) == "22222"
    assert validate_single_order_id("22222") == "22222"
    assert normalize_order_ids([22222, "111111"]) == "22222,111111"
    assert normalize_order_ids("22222, 111111") == "22222,111111"

    with pytest.raises(ValidationError, match="Expected a single order_id"):
        validate_single_order_id("22222,111111")
    with pytest.raises(ValidationError):
        validate_single_order_id([22222])  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        validate_single_order_id("not_numeric")
    with pytest.raises(ValidationError):
        normalize_order_ids([])


def test_format_csv_param() -> None:
    assert format_csv_param(None) is None
    assert format_csv_param("a,b") == "a,b"
    assert format_csv_param(123) == "123"
    assert format_csv_param(Currency.EUR) == "EUR"
    assert format_csv_param([Language.EN, "ES", 10, LinkType.NORMAL]) == "EN,ES,10,0"

    with pytest.raises(ValidationError):
        format_csv_param([{"bad": "item"}])  # type: ignore[list-item]


def test_product_and_order_models_coercions_and_pages() -> None:
    product = Product.model_validate(SAMPLE_PRODUCT_DICT)
    assert product.id == 33006951782
    assert product.product_id == 33006951782
    assert product.title == "Spring Autumn Dress"
    assert product.latest_volume == 300
    assert product.lastest_volume == 300
    assert product.sale_price_decimal == Decimal("15.9")
    assert product.target_sale_price_decimal == Decimal("350")
    assert product.original_price_decimal == Decimal("100")
    assert product.target_original_price_decimal == Decimal("380")
    assert product.app_sale_price_decimal == Decimal("20.5")
    assert product.target_app_sale_price_decimal == Decimal("330")
    assert product.commission_rate_pct == Decimal("3.5")
    assert product.hot_product_commission_rate_pct == Decimal("60")
    assert product.discount_pct == Decimal("50")
    assert product.evaluate_rate_pct == Decimal("89.2")
    assert product.tax_rate_decimal == Decimal("0.1")
    assert product.product_small_image_urls == [
        "https://ae01.alicdn.com/kf/img1.jpg",
        "https://ae01.alicdn.com/kf/img2.jpg",
    ]
    assert product.promo_code_info is not None
    assert product.promo_code_info.promo_code == "GMG20207"
    assert product.promo_code_info.code_quantity == 1
    assert product.promo_code_info.minimum_spend_decimal == Decimal("1")
    assert product.promo_code_info.available_start_datetime == datetime(2026, 4, 1, 0, 0, 0)
    assert product.promo_code_info.available_end_datetime == datetime(2026, 4, 30, 23, 59, 59)

    # Empty strings in optional int fields must safely coerce to None
    sparse_prod = Product.model_validate(
        {"product_id": "123", "second_level_category_id": "", "lastest_volume": ""}
    )
    assert sparse_prod.product_id == 123
    assert sparse_prod.second_level_category_id is None
    assert sparse_prod.latest_volume is None

    # Test Page[Product] conversion from ProductsResponse
    prod_resp = ProductsResponse.model_validate(
        {
            "current_page_no": "1",
            "current_record_count": "1",
            "total_record_count": "10",
            "total_page_no": "10",
            "is_finished": "false",
            "products": {"product": [SAMPLE_PRODUCT_DICT]},
        }
    )
    page: Page[Product] = prod_resp.to_page(requested_page_size=1)
    assert len(page) == 1
    assert page[0].product_id == 33006951782
    assert list(page) == [page[0]]
    assert page.page_no == 1
    assert page.page_size == 1
    assert page.total_count == 10
    assert page.total_pages == 10
    assert page.has_next is True
    assert page.products == page.items

    order = Order.model_validate(SAMPLE_ORDER_DICT)
    assert order.id == 22222
    assert order.order_id == 22222
    assert order.sub_order_id == 111111
    assert order.custom_parameters == '{"af":0,"dp":1111}'
    assert order.customer_parameters == '{"af":0,"dp":1111}'
    assert order.is_hot_product_bool is False
    assert order.is_new_buyer_bool is True
    assert order.is_affiliate_product_bool is False
    assert order.paid_amount_decimal == Decimal("1000")
    assert order.estimated_paid_commission_decimal == Decimal("22")
    assert order.commission_rate_pct == Decimal("3.5")
    assert order.incentive_commission_rate_pct == Decimal("3.5")
    assert order.estimated_incentive_paid_commission_decimal == Decimal("22")
    assert order.estimated_incentive_finished_commission_decimal == Decimal("17")
    assert order.new_buyer_bonus_commission_decimal == Decimal("12")
    assert order.paid_datetime == datetime(2026, 1, 15, 0, 5, 0)
    assert order.created_datetime == datetime(2026, 1, 15, 0, 0, 0)

    order_list_page = OrderListResponse.model_validate(
        {
            "current_page_no": 1,
            "current_record_count": 1,
            "total_record_count": 5,
            "total_page_no": 5,
            "orders": {"order": [SAMPLE_ORDER_DICT]},
        }
    ).to_page(requested_page_size=1)
    assert len(order_list_page) == 1
    assert order_list_page.total_count == 5
    assert order_list_page.has_next is True
    assert order_list_page.orders[0].order_id == 22222

    cursor_page: CursorPage[Order] = OrderListByIndexResponse.model_validate(
        {
            "current_record_count": 1,
            "min_query_index_id": "idx_1",
            "max_query_index_id": "idx_2",
            "orders": {"order": [SAMPLE_ORDER_DICT]},
        }
    ).to_cursor_page(requested_page_size=50)
    assert len(cursor_page) == 1
    assert cursor_page.has_next is True
    assert cursor_page.max_query_index_id == "idx_2"
    assert cursor_page[0].order_id == 22222


def test_links_categories_sku_and_promotion_models() -> None:
    links_resp = AffiliateLinksResponse.model_validate(
        {
            "total_result_count": "1",
            "tracking_id": "default",
            "promotion_links": {
                "promotion_link": [
                    {
                        "promotion_link": "http://s.click.aliexpress.com/e/123",
                        "source_value": "https://aliexpress.com",
                        "message": "Success",
                    }
                ]
            },
        }
    )
    assert len(links_resp.links) == 1
    assert links_resp.links[0].url == "http://s.click.aliexpress.com/e/123"

    cat_resp = CategoriesResponse.model_validate(
        {
            "total_result_count": 2,
            "categories": {
                "category": [
                    {"category_id": 10, "category_name": "Parent"},
                    {"category_id": 11, "category_name": "Child", "parent_category_id": 10},
                ]
            },
        }
    )
    assert cat_resp.categories[0].is_parent is True
    assert cat_resp.categories[0].id == 10
    assert cat_resp.categories[0].name == "Parent"
    assert cat_resp.categories[1].is_parent is False
    assert cat_resp.categories[1].parent_id == 10

    sku_detail = ProductSkuDetail.model_validate(
        {
            "ae_item_info": {
                "product_id": "1005004757833857",
                "title": "Deutscher Titel",
                "en_title": "English Title",
                "product_score": "4.8",
                "review_number": "12",
                "order_number": "130",
                "additional_image_links": {"string": ["https://img.example.com/1.jpg"]},
            },
            "ae_item_sku_info": {
                "traffic_sku_info_list": [
                    {
                        "sku_id": "12000030358585276",
                        "color": "WHITE",
                        "size": "S",
                        "price_with_tax": "22.32",
                        "sale_price_with_tax": "17.19",
                        "delivery_days": "5",
                        "min_delivery_days": "3",
                        "max_delivery_days": "7",
                    }
                ]
            },
        }
    )
    assert sku_detail.product_id == 1005004757833857
    assert sku_detail.item_info is not None
    assert sku_detail.item_info.product_id == 1005004757833857
    assert sku_detail.item_info.en_title == "English Title"
    assert sku_detail.item_info.review_number == 12
    assert sku_detail.item_info.order_number == 130
    assert sku_detail.item_info.product_score_decimal == Decimal("4.8")
    assert sku_detail.item_info.additional_image_links == ["https://img.example.com/1.jpg"]
    assert len(sku_detail.skus) == 1
    assert sku_detail.skus[0].sku_id == 12000030358585276
    assert sku_detail.skus[0].delivery_days == 5
    assert sku_detail.skus[0].sale_price_with_tax_decimal == Decimal("17.19")

    promo_resp = PromotionInfoResponse.model_validate(
        {
            "promotion_results": [
                {
                    "product_id": "1005006067128597",
                    "promotions": [
                        {
                            "generic_redemption_code": "AESAVE5",
                            "long_title": "$5.00 off on $50.00",
                            "money_off_amount": "5.00 USD",
                            "minimum_purchase_amount": "50.00 USD",
                        }
                    ],
                }
            ]
        }
    )
    result_item = promo_resp.promotion_results[0]
    assert result_item.product_id == 1005006067128597
    assert len(result_item) == 1
    coupon = result_item[0]
    assert coupon.redemption_code == "AESAVE5"
    assert coupon.generic_redemption_code == "AESAVE5"
    assert coupon.title == "$5.00 off on $50.00"
    assert coupon.money_off_decimal == Decimal("5.00")
    assert coupon.minimum_purchase_decimal == Decimal("50.00")
