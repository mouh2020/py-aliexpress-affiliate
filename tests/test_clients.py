"""End-to-end synchronous and asynchronous client tests using respx mocked HTTP."""

from __future__ import annotations

import asyncio
import urllib.parse
from decimal import Decimal
from typing import Any

import httpx
import pytest
import respx

from aliexpress_affiliate import (
    AffiliateLink,
    AliExpressClient,
    APIError,
    AsyncAliExpressClient,
    AuthenticationError,
    Category,
    CategoryNotFoundError,
    CursorPage,
    FeaturedPromo,
    FeaturedPromoSortBy,
    LinkGenerationError,
    LinkType,
    LocaleSite,
    NetworkError,
    Order,
    OrderNotFoundError,
    OrderStatus,
    OrderTimeType,
    Page,
    Product,
    ProductNotFoundError,
    ProductPromotionResult,
    ProductSkuDetail,
    ProductType,
    RateLimitError,
    ResourceNotFoundError,
    SignatureError,
    SortBy,
    ValidationError,
)

from .conftest import SAMPLE_ORDER_DICT, SAMPLE_PRODUCT_DICT

SYNC_URL = "https://api-sg.aliexpress.com/sync"


def _mock_all_15_handler(request: httpx.Request) -> httpx.Response:
    """Inspect ``method`` query param and return official AliExpress JSON response fixtures."""
    method = request.url.params.get("method", "")
    assert request.url.params.get("app_key") == "test_app_key"
    assert request.url.params.get("sign_method") == "md5"
    assert request.url.params.get("format") == "json"
    assert request.url.params.get("v") == "2.0"
    assert len(request.url.params.get("sign", "")) == 32

    body_params = dict(urllib.parse.parse_qsl(request.content.decode("utf-8")))

    if method == "aliexpress.affiliate.link.generate":
        assert body_params["tracking_id"] == "test_tracking_id"
        urls = [u.strip() for u in body_params["source_values"].split(",") if u.strip()]
        return httpx.Response(
            200,
            json={
                "aliexpress_affiliate_link_generate_response": {
                    "resp_result": {
                        "resp_code": "200",
                        "resp_msg": "success",
                        "result": {
                            "total_result_count": str(len(urls)),
                            "tracking_id": "test_tracking_id",
                            "promotion_links": [
                                {
                                    "promotion_link": "http://s.click.aliexpress.com/e/1sssdasdas",
                                    "message": "Success",
                                    "source_value": u,
                                }
                                for u in urls
                            ],
                        },
                    }
                },
                "code": "0",
                "request_id": "req_link_1",
            },
        )

    if method == "aliexpress.affiliate.category.get":
        return httpx.Response(
            200,
            json={
                "code": "0",
                "aliexpress_affiliate_category_get_response": {
                    "resp_result": {
                        "resp_code": "200",
                        "resp_msg": "success",
                        "result": {
                            "total_result_count": "2",
                            "categories": [
                                {"category_id": "200000345", "category_name": "Women's Clothing"},
                                {
                                    "category_id": "201303101",
                                    "category_name": "Blouses & Shirts",
                                    "parent_category_id": "200000345",
                                },
                            ],
                        },
                    }
                },
            },
        )

    if method == "aliexpress.affiliate.featuredpromo.get":
        return httpx.Response(
            200,
            json={
                "code": "0",
                "aliexpress_affiliate_featuredpromo_get_response": {
                    "resp_result": {
                        "resp_code": "200",
                        "resp_msg": "success",
                        "result": {
                            "current_record_count": "1",
                            "promos": [
                                {
                                    "promo_name": "Hot Product",
                                    "promo_desc": "High commission hot deals",
                                    "product_num": "100",
                                }
                            ],
                        },
                    }
                },
            },
        )

    if method in (
        "aliexpress.affiliate.featuredpromo.products.get",
        "aliexpress.affiliate.hotproduct.download",
        "aliexpress.affiliate.hotproduct.query",
        "aliexpress.affiliate.product.query",
        "aliexpress.affiliate.product.smartmatch",
        "aliexpress.affiliate.productdetail.get",
    ):
        if method == "aliexpress.affiliate.product.smartmatch" and "app" in body_params:
            assert body_params["app"] == "my_mobile_app"

        key = f"{method.replace('.', '_')}_response"
        return httpx.Response(
            200,
            json={
                "code": "0",
                key: {
                    "resp_result": {
                        "resp_code": "200",
                        "resp_msg": "success",
                        "result": {
                            "current_record_count": "1",
                            "total_record_count": "1",
                            "total_page_no": "1",
                            "current_page_no": "1",
                            "is_finished": "false",
                            "products": [SAMPLE_PRODUCT_DICT],
                        },
                    }
                },
            },
        )

    if method == "aliexpress.affiliate.product.shipping.get":
        return httpx.Response(
            200,
            json={
                "code": "0",
                "aliexpress_affiliate_product_shipping_get_response": {
                    "resp_result": {
                        "resp_code": "200",
                        "resp_msg": "success",
                        "result": {
                            "shipping_fee": "20.03",
                            "delivery_days": "5",
                            "max_delivery_days": "7",
                            "ship_from_country": "CN",
                            "min_delivery_days": "3",
                        },
                    }
                },
            },
        )

    if method == "aliexpress.affiliate.product.sku.detail.get":
        return httpx.Response(
            200,
            json={
                "code": "0",
                "aliexpress_affiliate_product_sku_detail_get_response": {
                    "result": {
                        "code": "200",
                        "success": "true",
                        "result": {
                            "ae_item_info": {
                                "product_id": "1005004757833857",
                                "title": "Localized Title",
                                "en_title": "Hot Sales Shirts",
                                "original_link": "https://www.aliexpress.com/item/1005004757833857.html",
                                "image_link": "https://ae-pic.aliexpress.com/1.jpg",
                                "image_white": "https://ae-pic.aliexpress.com/w.jpg",
                                "additional_image_links": [],
                                "product_category": "Women's Clothing",
                                "product_score": "5.0",
                                "review_number": "2",
                                "order_number": "130",
                                "brand": "BRANDX",
                                "display_category_id_l1": "200000345",
                                "display_category_name_l1": "Women",
                                "display_category_id_l2": "201303001",
                                "display_category_name_l2": "Tops",
                                "display_category_id_l3": "201303101",
                                "display_category_name_l3": "Shirts",
                            },
                            "ae_item_sku_info": [
                                {
                                    "sku_id": "12000030358585276",
                                    "color": "WHITE",
                                    "size": "S",
                                    "currency": "USD",
                                    "price_with_tax": "22.32",
                                    "sale_price_with_tax": "17.19",
                                    "discount_rate": "22",
                                    "tax_rate": "0.19",
                                    "shipping_fees": "20.03",
                                    "ship_from_country": "CN",
                                    "delivery_days": "5",
                                    "min_delivery_days": "3",
                                    "max_delivery_days": "7",
                                    "link": "https://www.aliexpress.com/item/1005004757833857.html",
                                    "sku_image_link": "https://ae-pic.aliexpress.com/sku.jpg",
                                }
                            ],
                        },
                    }
                },
            },
        )

    if method == "aliexpress.affiliate.promotion.info.get":
        return httpx.Response(
            200,
            json={
                "aliexpress_affiliate_promotion_info_get_response": {
                    "result": {
                        "promotion_results": [
                            {
                                "product_id": "1005006067128597",
                                "promotions": [
                                    {
                                        "redemption_channel": "online",
                                        "minimum_purchase_amount": "50.00 USD",
                                        "generic_redemption_code": "AESAVE5",
                                        "money_off_amount": "5.00 USD",
                                        "product_applicability": "specific_products",
                                        "coupon_value_type": "money_off",
                                        "offer_type": "generic_code",
                                        "long_title": "$5.00 off on $50.00",
                                        "promotion_effective_dates": "2026-03-19T03:00:00-07:00/2026-03-26T21:00:00-07:00",
                                    }
                                ],
                            }
                        ]
                    },
                    "msg": "success",
                    "code": "200",
                    "success": "true",
                },
                "code": "0",
            },
        )

    if method in (
        "aliexpress.affiliate.order.get",
        "aliexpress.affiliate.order.list",
        "aliexpress.affiliate.order.listbyindex",
    ):
        key = f"{method.replace('.', '_')}_response"
        result_body: dict[str, Any] = {
            "current_record_count": "1",
            "orders": [SAMPLE_ORDER_DICT],
        }
        if method == "aliexpress.affiliate.order.list":
            result_body["total_record_count"] = "1"
            result_body["total_page_no"] = "1"
            result_body["current_page_no"] = "1"
        elif method == "aliexpress.affiliate.order.listbyindex":
            result_body["min_query_index_id"] = "idx_min_1"
            result_body["max_query_index_id"] = "idx_max_1"
        return httpx.Response(
            200,
            json={
                "code": "0",
                key: {
                    "resp_result": {
                        "resp_code": "200",
                        "resp_msg": "success",
                        "result": result_body,
                    }
                },
            },
        )

    return httpx.Response(400, json={"error": f"Unknown method {method}"})


@respx.mock
def test_sync_client_all_15_methods() -> None:
    respx.post(SYNC_URL).mock(side_effect=_mock_all_15_handler)

    with AliExpressClient(
        app_key="test_app_key",
        app_secret="test_app_secret",
        tracking_id="test_tracking_id",
        country="US",
    ) as client:
        assert "test_app_secret" not in repr(client)

        # 1. link.generate (single & batch)
        single_link = client.generate_affiliate_link(
            "https://www.aliexpress.com/item/33006951782.html",
            promotion_link_type=LinkType.NORMAL,
        )
        assert isinstance(single_link, AffiliateLink)
        assert single_link.promotion_link == "http://s.click.aliexpress.com/e/1sssdasdas"
        assert single_link.tracking_id == "test_tracking_id"

        links = client.get_affiliate_links(["https://www.aliexpress.com/item/33006951782.html"])
        assert isinstance(links, list)
        assert links[0].promotion_link == "http://s.click.aliexpress.com/e/1sssdasdas"
        alias_links = client.generate_affiliate_links(
            ["https://www.aliexpress.com/item/33006951782.html"]
        )
        assert len(alias_links) == 1

        # 2. category.get (single & list helpers)
        cats = client.get_categories()
        assert len(cats) == 2
        single_cat = client.get_category(200000345, use_cache=True)
        assert isinstance(single_cat, Category)
        assert single_cat.category_name == "Women's Clothing"
        parents = client.get_parent_categories(use_cache=True)
        assert len(parents) == 1
        assert parents[0].category_id == 200000345
        children = client.get_child_categories(200000345, use_cache=True)
        assert len(children) == 1
        assert children[0].category_id == 201303101

        # 3. featuredpromo.get -> list[FeaturedPromo]
        promos = client.get_featured_promos()
        assert isinstance(promos, list)
        assert isinstance(promos[0], FeaturedPromo)
        assert promos[0].promo_name == "Hot Product"
        assert promos[0].name == "Hot Product"
        assert promos[0].promo_desc == "High commission hot deals"
        assert promos[0].product_num == 100

        # 4. featuredpromo.products.get -> Page[Product]
        fp_prods = client.get_featured_promo_products(
            promotion_name="Hot Product",
            sort=FeaturedPromoSortBy.COMMISSION_DESC,
        )
        assert isinstance(fp_prods, Page)
        assert len(fp_prods.items) == 1

        # 5. hotproduct.download -> Page[Product]
        dl_prods = client.download_hot_products(
            category_id=200000345,
            locale_site=LocaleSite.GLOBAL,
        )
        assert isinstance(dl_prods, Page)
        assert len(dl_prods.items) == 1

        # 6. hotproduct.query -> Page[Product]
        hot_prods = client.get_hot_products(
            keywords="dress",
            platform_product_type=ProductType.ALL,
            sort=SortBy.LAST_VOLUME_DESC,
        )
        assert isinstance(hot_prods, Page)
        assert len(hot_prods.items) == 1

        # 7. product.query -> Page[Product]
        prods = client.get_products(
            keywords="dress",
            category_ids=[200000345],
            delivery_days=5,
            min_sale_price=100,
            max_sale_price=5000,
        )
        assert isinstance(prods, Page)
        assert prods.items[0].product_id == 33006951782

        # 8. productdetail.get (single & batch)
        single_product = client.get_product_details(
            "https://www.aliexpress.com/item/33006951782.html"
        )
        assert isinstance(single_product, Product)
        assert single_product.product_id == 33006951782

        batch_products = client.get_products_details(["33006951782"])
        assert isinstance(batch_products, list)
        assert batch_products[0].product_id == 33006951782

        # 9. product.smartmatch -> Page[Product]
        smart = client.smart_match_products(
            device_id="dev_123",
            app="my_mobile_app",
            keywords="dress",
        )
        assert isinstance(smart, Page)
        assert len(smart.items) == 1

        # 10. product.shipping.get -> ProductShippingInfo
        shipping = client.get_product_shipping_info(
            product_id=33006951782,
            sku_id=12000029786932962,
            target_sale_price=Decimal("15.9"),
            tax_rate=Decimal("0.1"),
        )
        assert shipping.shipping_fee == "20.03"
        assert shipping.shipping_fee_decimal == Decimal("20.03")
        assert shipping.delivery_days == 5
        assert shipping.min_delivery_days == 3
        assert shipping.max_delivery_days == 7
        assert shipping.ship_from_country == "CN"

        # 11. product.sku.detail.get -> ProductSkuDetail
        sku_detail = client.get_product_sku_details(
            "1005004757833857",
            need_deliver_info=True,
        )
        assert isinstance(sku_detail, ProductSkuDetail)
        assert sku_detail.item_info is not None
        assert sku_detail.item_info.brand == "BRANDX"
        assert sku_detail.skus[0].color == "WHITE"
        assert sku_detail.skus[0].delivery_days == 5

        # 12. promotion.info.get (single & batch)
        single_promo = client.get_promotion_info("1005006067128597")
        assert isinstance(single_promo, ProductPromotionResult)
        assert single_promo.promotions[0].redemption_code == "AESAVE5"

        batch_promos = client.get_promotions_info(["1005006067128597"])
        assert isinstance(batch_promos, list)
        assert batch_promos[0].promotions[0].redemption_code == "AESAVE5"

        # 13. order.get (single & batch)
        single_order = client.get_order_details(22222)
        assert isinstance(single_order, Order)
        assert single_order.order_id == 22222
        assert not hasattr(single_order, "current_record_count")

        batch_orders = client.get_orders_details([22222])
        assert isinstance(batch_orders, list)
        assert batch_orders[0].order_id == 22222

        # 14. order.list -> Page[Order]
        order_list = client.get_order_list(
            status=OrderStatus.PAYMENT_COMPLETED,
            start_time="2026-01-01 00:00:00",
            end_time="2026-01-07 23:59:59",
            time_type=OrderTimeType.PAYMENT_COMPLETED_TIME,
        )
        assert isinstance(order_list, Page)
        assert order_list.total_count == 1
        assert order_list.items[0].order_id == 22222

        # 15. order.listbyindex -> CursorPage[Order]
        order_idx = client.get_order_list_by_index(
            status=OrderStatus.PAYMENT_COMPLETED,
            start_time="2026-01-01 00:00:00",
            end_time="2026-01-07 23:59:59",
        )
        assert isinstance(order_idx, CursorPage)
        assert order_idx.max_query_index_id == "idx_max_1"
        assert order_idx.has_next is True


@respx.mock
def test_async_client_all_15_methods() -> None:
    respx.post(SYNC_URL).mock(side_effect=_mock_all_15_handler)

    async def _run() -> None:
        async with AsyncAliExpressClient(
            app_key="test_app_key",
            app_secret="test_app_secret",
            tracking_id="test_tracking_id",
            country="US",
        ) as client:
            assert "test_app_secret" not in repr(client)

            single_link = await client.generate_affiliate_link(
                "https://www.aliexpress.com/item/33006951782.html"
            )
            assert isinstance(single_link, AffiliateLink)
            links = await client.get_affiliate_links(
                ["https://www.aliexpress.com/item/33006951782.html"]
            )
            assert len(links) == 1
            alias_links = await client.generate_affiliate_links(
                ["https://www.aliexpress.com/item/33006951782.html"]
            )
            assert len(alias_links) == 1

            cats = await client.get_categories()
            assert len(cats) == 2
            cat = await client.get_category(200000345)
            assert cat.category_id == 200000345
            parents = await client.get_parent_categories()
            assert len(parents) == 1
            children = await client.get_child_categories(200000345)
            assert len(children) == 1

            promos = await client.get_featured_promos()
            assert len(promos) == 1

            fp_prods = await client.get_featured_promo_products(promotion_name="Hot Product")
            assert len(fp_prods.items) == 1

            dl_prods = await client.download_hot_products(category_id="200000345")
            assert len(dl_prods.items) == 1

            hot_prods = await client.get_hot_products(keywords="dress")
            assert len(hot_prods.items) == 1

            prods = await client.get_products(keywords="dress")
            assert len(prods.items) == 1

            single_detail = await client.get_product_details(33006951782)
            assert isinstance(single_detail, Product)
            batch_details = await client.get_products_details([33006951782])
            assert len(batch_details) == 1

            smart = await client.smart_match_products(device_id="dev_1", app="my_mobile_app")
            assert len(smart.items) == 1

            shipping = await client.get_product_shipping_info(
                product_id=33006951782,
                sku_id=12000029786932962,
                target_sale_price="15.9",
                tax_rate="0.1",
            )
            assert shipping.delivery_days == 5

            sku_detail = await client.get_product_sku_details("1005004757833857")
            assert len(sku_detail.skus) == 1

            single_promo = await client.get_promotion_info("1005006067128597")
            assert isinstance(single_promo, ProductPromotionResult)
            batch_promos = await client.get_promotions_info(["1005006067128597"])
            assert len(batch_promos) == 1

            single_order = await client.get_order_details(22222)
            assert isinstance(single_order, Order)
            batch_orders = await client.get_orders_details([22222])
            assert len(batch_orders) == 1

            order_list = await client.get_order_list(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-07 23:59:59",
            )
            assert len(order_list.items) == 1

            order_idx = await client.get_order_list_by_index(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-07 23:59:59",
            )
            assert order_idx.min_query_index_id == "idx_min_1"

    asyncio.run(_run())


@respx.mock
def test_single_item_not_found_exceptions(
    sync_client: AliExpressClient, async_client: AsyncAliExpressClient
) -> None:
    # 1. ProductNotFoundError on get_product_details (sync & async)
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "resp_result": {
                    "resp_code": "200",
                    "resp_msg": "success",
                    "result": {"current_record_count": "0", "products": []},
                }
            },
        )
    )
    with pytest.raises(ProductNotFoundError) as prod_exc:
        sync_client.get_product_details(999999999)
    assert prod_exc.value.product_id == "999999999"

    async def _check_async_product_not_found() -> None:
        with pytest.raises(ProductNotFoundError):
            await async_client.get_product_details(999999999)

    asyncio.run(_check_async_product_not_found())

    # Reject passing a list or comma-separated IDs to single-item get_product_details
    with pytest.raises(ValidationError):
        sync_client.get_product_details([111, 222])  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="Expected a single product_id"):
        sync_client.get_product_details("111,222")

    # 2. OrderNotFoundError on get_order_details (sync & async)
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "resp_result": {
                    "resp_code": "200",
                    "resp_msg": "success",
                    "result": {"current_record_count": "0", "orders": []},
                }
            },
        )
    )
    with pytest.raises(OrderNotFoundError) as ord_exc:
        sync_client.get_order_details(88888888)
    assert ord_exc.value.order_id == "88888888"

    async def _check_async_order_not_found() -> None:
        with pytest.raises(OrderNotFoundError):
            await async_client.get_order_details(88888888)

    asyncio.run(_check_async_order_not_found())

    # Reject passing a list or comma-separated IDs to single-item get_order_details
    with pytest.raises(ValidationError):
        sync_client.get_order_details([22222, 33333])  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="Expected a single order_id"):
        sync_client.get_order_details("22222,33333")

    # 3. LinkGenerationError on generate_affiliate_link when empty or promotion_link is None
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "resp_result": {
                    "resp_code": "200",
                    "resp_msg": "success",
                    "result": {
                        "total_result_count": 0,
                        "promotion_links": [
                            {
                                "source_value": "https://bad.example.com",
                                "message": "Target URL is not an affiliate product",
                            }
                        ],
                    },
                }
            },
        )
    )
    with pytest.raises(LinkGenerationError, match="Target URL is not an affiliate product"):
        sync_client.generate_affiliate_link("https://bad.example.com")

    # 4. CategoryNotFoundError on get_category
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "resp_result": {
                    "resp_code": "200",
                    "resp_msg": "success",
                    "result": {
                        "total_result_count": 1,
                        "categories": [{"category_id": 100, "category_name": "Toys"}],
                    },
                }
            },
        )
    )
    with pytest.raises(CategoryNotFoundError) as cat_exc:
        sync_client.get_category(999, use_cache=False)
    assert cat_exc.value.category_id == "999"

    # 5. ProductNotFoundError on get_promotion_info when empty
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "aliexpress_affiliate_promotion_info_get_response": {
                    "result": {"promotion_results": []},
                    "code": "200",
                    "success": "true",
                }
            },
        )
    )
    with pytest.raises(ProductNotFoundError):
        sync_client.get_promotion_info("1005006067128597")


@respx.mock
def test_error_mapping_and_retries(sync_client: AliExpressClient) -> None:
    # 1. SignatureError
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "error_response": {
                    "code": "25",
                    "msg": "Invalid signature",
                    "sub_code": "isv.invalid-signature",
                    "request_id": "req_sig_err",
                }
            },
        )
    )
    with pytest.raises(SignatureError) as sig_exc:
        sync_client.get_categories()
    assert sig_exc.value.code == "25"
    assert sig_exc.value.request_id == "req_sig_err"
    assert "code=25" in str(sig_exc.value)

    # 2. AuthenticationError
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "error_response": {
                    "code": "29",
                    "msg": "Invalid appKey",
                    "sub_msg": "AppKey does not exist",
                }
            },
        )
    )
    with pytest.raises(AuthenticationError):
        sync_client.get_categories()

    # 3. RateLimitError from TOP payload and from HTTP 429
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "error_response": {
                    "code": "7",
                    "msg": "App Call Limited",
                    "sub_code": "accesscontrol.limited-by-api-access-count",
                }
            },
        )
    )
    with pytest.raises(RateLimitError):
        sync_client.get_categories()

    respx.post(SYNC_URL).mock(return_value=httpx.Response(429, text="Too Many Requests"))
    with pytest.raises(RateLimitError):
        sync_client.get_categories()

    # 4. Business-level 405 Not Found on get_product_sku_details -> ProductNotFoundError
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "aliexpress_affiliate_product_sku_detail_get_response": {
                    "result": {
                        "code": "405",
                        "success": "false",
                        "msg": "No query results were found for the input parameter",
                    }
                }
            },
        )
    )
    with pytest.raises(ProductNotFoundError) as api_exc:
        sync_client.get_product_sku_details("1005004757833857")
    assert api_exc.value.code == "405"
    assert isinstance(api_exc.value, APIError)

    # 5. Retry on 503 then succeed
    attempts = 0

    def _flaky_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(
            200,
            json={
                "resp_result": {
                    "resp_code": "200",
                    "resp_msg": "success",
                    "result": {"total_result_count": 0, "categories": []},
                }
            },
        )

    respx.post(SYNC_URL).mock(side_effect=_flaky_handler)
    cats = sync_client.get_categories()
    assert cats == []
    assert attempts == 2

    # 6. Exhaust retries on network timeout -> NetworkError
    respx.post(SYNC_URL).mock(side_effect=httpx.ConnectTimeout("Timed out"))
    with pytest.raises(NetworkError, match="HTTP request failed"):
        sync_client.get_categories()


def test_sync_and_async_client_method_parity() -> None:
    """Verify AliExpressClient and AsyncAliExpressClient expose the exact same public API methods."""
    lifecycle_only = {"close", "aclose"}
    sync_methods = {
        name
        for name in dir(AliExpressClient)
        if not name.startswith("_")
        and callable(getattr(AliExpressClient, name))
        and name not in lifecycle_only
    }
    async_methods = {
        name
        for name in dir(AsyncAliExpressClient)
        if not name.startswith("_")
        and callable(getattr(AsyncAliExpressClient, name))
        and name not in lifecycle_only
    }
    assert sync_methods == async_methods


@respx.mock
def test_validation_and_raise_on_empty() -> None:
    client = AliExpressClient(
        app_key="k",
        app_secret="s",
        tracking_id=None,
        country=None,
        raise_on_empty=True,
    )
    with pytest.raises(ValidationError, match="tracking_id"):
        client.get_affiliate_links("https://www.aliexpress.com/item/33006951782.html")

    with pytest.raises(ValidationError, match="ship_to_country"):
        client.get_product_sku_details("1005004757833857")

    with pytest.raises(ValidationError, match="At least one of"):
        client.smart_match_products()

    with pytest.raises(ValidationError, match="at most 10"):
        client.get_promotions_info([str(i + 1) for i in range(11)], ship_to_country="US")

    with pytest.raises(ValidationError, match="at most 50"):
        client.get_affiliate_links(
            [f"https://aliexpress.com/item/{i + 1}.html" for i in range(51)],
            tracking_id="trk",
        )

    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "resp_result": {
                    "resp_code": "200",
                    "resp_msg": "success",
                    "result": {"current_record_count": 0, "products": []},
                }
            },
        )
    )
    with pytest.raises(ResourceNotFoundError):
        client.get_products(keywords="nothing")
    client.close()


@respx.mock
def test_sanitized_live_response_snapshots(
    sanitized_live_fixtures: dict[str, Any],
    sync_client: AliExpressClient,
    async_client: AsyncAliExpressClient,
) -> None:
    """Replay sanitized real AliExpress API snapshots through both sync and async clients."""

    def _live_snapshot_handler(request: httpx.Request) -> httpx.Response:
        method = request.url.params.get("method", "")
        mapping = {
            "aliexpress.affiliate.category.get": "category_get",
            "aliexpress.affiliate.featuredpromo.get": "featuredpromo_get",
            "aliexpress.affiliate.product.query": "product_query",
            "aliexpress.affiliate.productdetail.get": "productdetail_get",
            "aliexpress.affiliate.product.shipping.get": "product_shipping_get",
            "aliexpress.affiliate.product.sku.detail.get": "product_sku_detail_get",
            "aliexpress.affiliate.link.generate": "link_generate",
            "aliexpress.affiliate.promotion.info.get": "error_top_405_empty",
            "aliexpress.affiliate.order.list": "order_list",
            "aliexpress.affiliate.order.listbyindex": "order_listbyindex",
            "aliexpress.affiliate.order.get": "order_get",
        }
        fixture_key = mapping[method]
        return httpx.Response(200, json=sanitized_live_fixtures[fixture_key])

    respx.post(SYNC_URL).mock(side_effect=_live_snapshot_handler)

    # 1. Categories
    cats = sync_client.get_categories()
    assert len(cats) == 3
    assert cats[0].category_id == 2
    assert cats[0].is_parent is True
    assert cats[1].parent_category_id == 2

    # 2. Featured promos
    promos = sync_client.get_featured_promos()
    assert len(promos) == 2
    assert promos[0].promo_name == "1009-1011 Brand day - Bestsellers"
    assert promos[0].product_num == 3000

    # 3. Product query & product details
    prod_page = sync_client.get_products(keywords="wireless mouse")
    assert prod_page.items[0].product_id == 3256812587562514
    assert prod_page.items[0].sku_id == 12000059297537459
    assert prod_page.items[0].sale_price_decimal == Decimal("657.09")
    assert prod_page.items[0].target_sale_price_decimal == Decimal("98.69")

    detail = sync_client.get_product_details(3256812587562514)
    assert detail.product_id == 3256812587562514

    # 4. Shipping info
    ship = sync_client.get_product_shipping_info(
        product_id=3256812587562514,
        sku_id=12000059297537459,
        target_sale_price="98.69",
        tax_rate="0.00",
    )
    assert ship.shipping_fee_decimal == Decimal("1.99")
    assert ship.delivery_days == 12
    assert ship.min_delivery_days == 7
    assert ship.max_delivery_days == 12

    # 5. SKU details (live traffic_sku_info_list wrapper)
    sku_detail = sync_client.get_product_sku_details(3256812587562514)
    assert sku_detail.product_id == 3256812587562514
    assert sku_detail.item_info is not None
    assert len(sku_detail.skus) == 2
    assert sku_detail.skus[0].sku_id == 12000059297537457
    assert sku_detail.skus[0].color == "X1V2 Ultimate Plus W"
    assert sku_detail.skus[0].sale_price_with_tax_decimal == Decimal("98.99")

    # 6. Link generation
    link = sync_client.generate_affiliate_link(
        "https://www.aliexpress.com/item/3256812587562514.html"
    )
    assert link.promotion_link == "https://s.click.aliexpress.com/e/_sanitized"

    # 7. Promotion info empty result (ERROR-405) -> [] on batch, ProductNotFoundError on single
    assert sync_client.get_promotions_info([3256812587562514]) == []
    with pytest.raises(ProductNotFoundError) as promo_nf:
        sync_client.get_promotion_info(3256812587562514)
    assert promo_nf.value.sub_code == "ERROR-405"

    # 8. Orders (order.list, order.listbyindex, order.get by sub_order_id)
    order_page = sync_client.get_order_list(
        status=OrderStatus.PAYMENT_COMPLETED,
        start_time="2026-10-01 00:00:00",
        end_time="2026-10-13 23:59:59",
    )
    assert order_page.total_count == 1
    assert order_page.items[0].order_id == 3000000000000001
    assert order_page.items[0].sub_order_id == 3000000000010001
    assert order_page.items[0].paid_amount_decimal == Decimal("31")
    assert order_page.items[0].commission_rate_pct == Decimal("15.00")
    assert order_page.items[0].incentive_commission_rate_pct == Decimal("8.00")

    cursor_page = sync_client.get_order_list_by_index(
        status=OrderStatus.PAYMENT_COMPLETED,
        start_time="2026-10-01 00:00:00",
        end_time="2026-10-13 23:59:59",
    )
    assert len(cursor_page.items) == 1
    assert cursor_page.min_query_index_id is not None

    single_order = sync_client.get_order_details(3000000000010001)
    assert single_order.sub_order_id == 3000000000010001
    assert single_order.order_id == 3000000000000001

    async def _verify_async_parity() -> None:
        async_sku = await async_client.get_product_sku_details(3256812587562514)
        assert len(async_sku.skus) == 2
        assert await async_client.get_promotions_info([3256812587562514]) == []
        with pytest.raises(ProductNotFoundError):
            await async_client.get_promotion_info(3256812587562514)
        async_order = await async_client.get_order_details(3000000000010001)
        assert async_order.sub_order_id == 3000000000010001

    asyncio.run(_verify_async_parity())


@respx.mock
def test_live_error_envelopes_and_rate_limit_retry(
    sanitized_live_fixtures: dict[str, Any],
    sync_client: AliExpressClient,
    async_client: AsyncAliExpressClient,
) -> None:
    """Verify live error envelopes (IncompleteSignature, InvalidAppKey, ApiCallLimit, 405)."""
    # 1. IncompleteSignature -> SignatureError
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(200, json=sanitized_live_fixtures["error_incomplete_signature"])
    )
    with pytest.raises(SignatureError) as sig_exc:
        sync_client.get_categories()
    assert sig_exc.value.code == "IncompleteSignature"

    # 2. InvalidAppKey -> AuthenticationError
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(200, json=sanitized_live_fixtures["error_invalid_app_key"])
    )
    with pytest.raises(AuthenticationError) as auth_exc:
        sync_client.get_categories()
    assert auth_exc.value.code == "InvalidAppKey"

    # 3. TOP code="15", sub_code="ERROR-405" and business resp_code=405 ("The result is empty")
    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(200, json=sanitized_live_fixtures["error_business_405_empty"])
    )
    with pytest.raises(OrderNotFoundError) as ord_nf:
        sync_client.get_order_details(9999999999999999)
    assert ord_nf.value.code == "405"

    assert sync_client.get_orders_details([9999999999999999]) == []

    respx.post(SYNC_URL).mock(
        return_value=httpx.Response(200, json=sanitized_live_fixtures["error_top_405_empty"])
    )
    empty_orders_page = sync_client.get_order_list(
        status=OrderStatus.PAYMENT_COMPLETED,
        start_time="2020-01-01 00:00:00",
        end_time="2020-01-02 00:00:00",
    )
    assert empty_orders_page.items == []
    assert empty_orders_page.total_count == 0

    empty_prods_page = sync_client.get_products(keywords="zzzznonexistent9999")
    assert empty_prods_page.items == []

    # 4. ApiCallLimit -> retried automatically when max_retries > 0, then succeeds
    call_count = 0

    def _rate_limited_then_ok(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=sanitized_live_fixtures["error_api_call_limit"])
        return httpx.Response(200, json=sanitized_live_fixtures["category_get"])

    respx.post(SYNC_URL).mock(side_effect=_rate_limited_then_ok)
    cats = sync_client.get_categories()
    assert len(cats) == 3
    assert call_count == 2

    # Async retry on ApiCallLimit
    async_calls = 0

    def _async_rate_limited_then_ok(request: httpx.Request) -> httpx.Response:
        nonlocal async_calls
        async_calls += 1
        if async_calls == 1:
            return httpx.Response(200, json=sanitized_live_fixtures["error_api_call_limit"])
        return httpx.Response(200, json=sanitized_live_fixtures["category_get"])

    respx.post(SYNC_URL).mock(side_effect=_async_rate_limited_then_ok)

    async def _run_async_retry() -> None:
        res = await async_client.get_categories()
        assert len(res) == 3

    asyncio.run(_run_async_retry())
    assert async_calls == 2
