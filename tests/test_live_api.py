"""Live integration tests against the real AliExpress Affiliate API.

Skipped by default. Run with::

    pytest -m live --run-live
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from aliexpress_affiliate import (
    AffiliateLink,
    AliExpressClient,
    AsyncAliExpressClient,
    AuthenticationError,
    Category,
    CategoryNotFoundError,
    ChildCategory,
    Currency,
    CursorPage,
    FeaturedPromo,
    Language,
    LinkGenerationError,
    Order,
    OrderNotFoundError,
    OrderStatus,
    Page,
    Product,
    ProductNotFoundError,
    ProductPromotionResult,
    ProductShippingInfo,
    ProductSkuDetail,
    SignatureError,
    ValidationError,
)

pytestmark = pytest.mark.live

RATE_LIMIT_DELAY_SEC = 1.2


def _throttle() -> None:
    """Sleep briefly between live API calls to respect the 1 QPS gateway rate limit."""
    time.sleep(RATE_LIMIT_DELAY_SEC)


def _make_sync_client() -> AliExpressClient:
    return AliExpressClient(
        language=Language.EN,
        currency=Currency.USD,
        country="US",
        max_retries=3,
        backoff_factor=1.0,
    )


def _make_async_client() -> AsyncAliExpressClient:
    return AsyncAliExpressClient(
        language=Language.EN,
        currency=Currency.USD,
        country="US",
        max_retries=3,
        backoff_factor=1.0,
    )


@dataclass(frozen=True)
class DiscoveredLiveTestData:
    """Session-scoped container holding IDs dynamically discovered from the live API."""

    parent_category_id: int
    child_category_id: int
    hot_download_category_id: int
    promo_name: str
    product_id: int
    second_product_id: int
    product_url: str
    sku_id: int
    target_sale_price: str
    tax_rate: str
    order_start_time: str
    order_end_time: str
    sub_order_id: int | None
    parent_order_id: int | None


@pytest.fixture(scope="session")
def live_data() -> DiscoveredLiveTestData:
    """Discover real categories, promos, products, SKUs, and orders dynamically."""
    with _make_sync_client() as client:
        # 1. Discover categories
        categories = client.get_categories()
        assert len(categories) > 0, "Expected live API to return categories"
        parents = [c for c in categories if c.is_parent]
        children = [c for c in categories if not c.is_parent and c.parent_category_id is not None]
        assert len(parents) > 0 and len(children) > 0
        first_child = children[0]
        assert first_child.parent_category_id is not None
        parent_category_id = first_child.parent_category_id
        child_category_id = first_child.category_id
        _throttle()

        # 2. Discover featured promos with non-zero products for US
        promos = client.get_featured_promos()
        assert len(promos) > 0, "Expected live API to return featured promotions"
        _throttle()
        non_empty_promos = [p for p in promos if (p.product_num or 0) > 0]
        promo_name = non_empty_promos[0].promo_name if non_empty_promos else promos[0].promo_name
        for candidate_promo in non_empty_promos:
            if (
                "Bestsellers" in candidate_promo.promo_name
                or not candidate_promo.promo_name.endswith(("-PE", "-CL", "-BR", "-KR", "-MX"))
            ):
                check_prods = client.get_featured_promo_products(
                    promotion_name=candidate_promo.promo_name,
                    page_size=5,
                )
                _throttle()
                if check_prods.items:
                    promo_name = candidate_promo.promo_name
                    break

        # 3. Discover products with valid sku_id and non-empty shipping info
        product_page = client.get_products(
            keywords="wireless mouse",
            category_ids=44,
            ship_to_country="US",
            page_size=10,
        )
        _throttle()
        if len(product_page.items) < 2:
            product_page = client.get_products(
                category_ids=44,
                ship_to_country="US",
                page_size=10,
            )
            _throttle()
        assert len(product_page.items) >= 2, "Expected at least 2 products from product.query"
        chosen_product: Product = product_page.items[0]
        for candidate in product_page.items[:5]:
            if candidate.sku_id is None or not candidate.product_detail_url:
                continue
            cand_price = candidate.target_sale_price or candidate.sale_price or "10.00"
            cand_tax = candidate.tax_rate or "0.0"
            ship_check = client.get_product_shipping_info(
                product_id=candidate.product_id,
                sku_id=candidate.sku_id,
                ship_to_country="US",
                target_sale_price=cand_price,
                target_currency=Currency.USD,
                target_language=Language.EN,
                tax_rate=cand_tax,
            )
            _throttle()
            if ship_check.delivery_days is not None:
                chosen_product = candidate
                break
        second_product = next(
            p for p in product_page.items if p.product_id != chosen_product.product_id
        )
        assert chosen_product.sku_id is not None
        hot_download_category_id = chosen_product.first_level_category_id or 44
        product_url = (
            chosen_product.product_detail_url
            or f"https://www.aliexpress.com/item/{chosen_product.product_id}.html"
        )
        target_sale_price = chosen_product.target_sale_price or chosen_product.sale_price or "10.00"
        tax_rate = chosen_product.tax_rate or "0.0"

        # 4. Discover recent orders across 29-day windows (up to 6 months back)
        now = datetime(2026, 10, 13, 23, 59, 59)
        discovered_sub_order_id: int | None = None
        discovered_parent_order_id: int | None = None
        order_start_str = "2026-10-01 00:00:00"
        order_end_str = "2026-10-13 23:59:59"

        for window_idx in range(6):
            w_end = now - timedelta(days=window_idx * 29)
            w_start = w_end - timedelta(days=28)
            start_str = w_start.strftime("%Y-%m-%d 00:00:00")
            end_str = w_end.strftime("%Y-%m-%d 23:59:59")
            page = client.get_order_list(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time=start_str,
                end_time=end_str,
                page_size=20,
            )
            _throttle()
            if page.items:
                first_order = page.items[0]
                discovered_sub_order_id = first_order.sub_order_id or first_order.order_number
                discovered_parent_order_id = first_order.order_id
                order_start_str = start_str
                order_end_str = end_str
                break

        return DiscoveredLiveTestData(
            parent_category_id=parent_category_id,
            child_category_id=child_category_id,
            hot_download_category_id=hot_download_category_id,
            promo_name=promo_name,
            product_id=chosen_product.product_id,
            second_product_id=second_product.product_id,
            product_url=product_url,
            sku_id=chosen_product.sku_id,
            target_sale_price=target_sale_price,
            tax_rate=tax_rate,
            order_start_time=order_start_str,
            order_end_time=order_end_str,
            sub_order_id=discovered_sub_order_id,
            parent_order_id=discovered_parent_order_id,
        )


def test_live_categories_sync_and_async(live_data: DiscoveredLiveTestData) -> None:
    """Verify get_categories, get_category, get_parent_categories, and get_child_categories."""
    with _make_sync_client() as sync_client:
        sync_cats = sync_client.get_categories()
        assert isinstance(sync_cats, list)
        assert len(sync_cats) > 0
        assert isinstance(sync_cats[0], Category)
        assert isinstance(sync_cats[0].category_id, int)
        assert bool(sync_cats[0].category_name)

        sync_single = sync_client.get_category(live_data.parent_category_id, use_cache=True)
        assert isinstance(sync_single, Category)
        assert sync_single.category_id == live_data.parent_category_id
        assert sync_single.is_parent is True

        sync_parents = sync_client.get_parent_categories(use_cache=True)
        assert len(sync_parents) > 0
        assert all(c.is_parent for c in sync_parents)

        sync_children = sync_client.get_child_categories(
            live_data.parent_category_id, use_cache=True
        )
        assert len(sync_children) > 0
        assert any(c.category_id == live_data.child_category_id for c in sync_children)

    _throttle()

    async def _run_async() -> tuple[list[Category], Category, list[Category], list[ChildCategory]]:
        async with _make_async_client() as async_client:
            a_cats = await async_client.get_categories()
            a_single = await async_client.get_category(live_data.parent_category_id, use_cache=True)
            a_parents = await async_client.get_parent_categories(use_cache=True)
            a_children = await async_client.get_child_categories(
                live_data.parent_category_id, use_cache=True
            )
            return a_cats, a_single, a_parents, a_children

    async_cats, async_single, async_parents, async_children = asyncio.run(_run_async())
    assert len(async_cats) == len(sync_cats)
    assert async_single.category_id == sync_single.category_id
    assert len(async_parents) == len(sync_parents)
    assert len(async_children) == len(sync_children)
    _throttle()


def test_live_featured_promos_and_products_sync_and_async(
    live_data: DiscoveredLiveTestData,
) -> None:
    """Verify get_featured_promos and get_featured_promo_products on sync and async clients."""
    with _make_sync_client() as sync_client:
        sync_promos = sync_client.get_featured_promos()
        assert isinstance(sync_promos, list)
        assert len(sync_promos) > 0
        assert isinstance(sync_promos[0], FeaturedPromo)
        assert bool(sync_promos[0].promo_name)
        _throttle()

        sync_promo_prods = sync_client.get_featured_promo_products(
            promotion_name=live_data.promo_name,
            page_size=5,
        )
        assert isinstance(sync_promo_prods, Page)
        assert len(sync_promo_prods.items) > 0
        assert isinstance(sync_promo_prods.items[0], Product)
        _throttle()

    async def _run_async() -> tuple[list[FeaturedPromo], Page[Product]]:
        async with _make_async_client() as async_client:
            a_promos = await async_client.get_featured_promos()
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_prods = await async_client.get_featured_promo_products(
                promotion_name=live_data.promo_name,
                page_size=5,
            )
            return a_promos, a_prods

    async_promos, async_promo_prods = asyncio.run(_run_async())
    assert len(async_promos) == len(sync_promos)
    assert len(async_promo_prods.items) == len(sync_promo_prods.items)
    assert async_promo_prods.items[0].product_id == sync_promo_prods.items[0].product_id
    _throttle()


def test_live_product_queries_and_details_sync_and_async(
    live_data: DiscoveredLiveTestData,
) -> None:
    """Verify download_hot_products, get_hot_products, get_products, smart_match, and details."""
    with _make_sync_client() as sync_client:
        sync_dl = sync_client.download_hot_products(
            category_id=live_data.hot_download_category_id, page_size=5
        )
        assert isinstance(sync_dl, Page)
        assert len(sync_dl.items) > 0
        _throttle()

        sync_hot = sync_client.get_hot_products(
            category_ids=live_data.hot_download_category_id, page_size=5
        )
        assert isinstance(sync_hot, Page)
        assert len(sync_hot.items) > 0
        _throttle()

        sync_query = sync_client.get_products(
            category_ids=live_data.hot_download_category_id, page_size=5
        )
        assert isinstance(sync_query, Page)
        assert len(sync_query.items) > 0
        assert isinstance(sync_query.items[0].sale_price_decimal, Decimal)
        _throttle()

        sync_smart = sync_client.smart_match_products(
            device_id="live_test_device_001",
            product_id=live_data.product_id,
            page_no=1,
        )
        assert isinstance(sync_smart, Page)
        assert len(sync_smart.items) > 0
        _throttle()

        sync_single = sync_client.get_product_details(live_data.product_id)
        assert isinstance(sync_single, Product)
        assert sync_single.product_id == live_data.product_id
        assert bool(sync_single.product_title)
        assert isinstance(sync_single.sale_price_decimal, Decimal)
        _throttle()

        sync_batch = sync_client.get_products_details(
            [live_data.product_id, live_data.second_product_id]
        )
        assert isinstance(sync_batch, list)
        assert len(sync_batch) >= 1
        assert any(p.product_id == live_data.product_id for p in sync_batch)
        _throttle()

    async def _run_async() -> tuple[
        Page[Product],
        Page[Product],
        Page[Product],
        Page[Product],
        Product,
        list[Product],
    ]:
        async with _make_async_client() as async_client:
            a_dl = await async_client.download_hot_products(
                category_id=live_data.hot_download_category_id, page_size=5
            )
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_hot = await async_client.get_hot_products(
                category_ids=live_data.hot_download_category_id, page_size=5
            )
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_query = await async_client.get_products(
                category_ids=live_data.hot_download_category_id, page_size=5
            )
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_smart = await async_client.smart_match_products(
                device_id="live_test_device_001",
                product_id=live_data.product_id,
                page_no=1,
            )
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_single = await async_client.get_product_details(live_data.product_id)
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_batch = await async_client.get_products_details(
                [live_data.product_id, live_data.second_product_id]
            )
            return a_dl, a_hot, a_query, a_smart, a_single, a_batch

    a_dl, a_hot, a_query, a_smart, a_single, a_batch = asyncio.run(_run_async())
    assert len(a_dl.items) == len(sync_dl.items)
    assert len(a_hot.items) == len(sync_hot.items)
    assert len(a_query.items) == len(sync_query.items)
    assert len(a_smart.items) == len(sync_smart.items)
    assert a_single.product_id == sync_single.product_id
    assert a_single.sale_price_decimal == sync_single.sale_price_decimal
    assert len(a_batch) == len(sync_batch)
    _throttle()


def test_live_shipping_and_sku_details_sync_and_async(
    live_data: DiscoveredLiveTestData,
) -> None:
    """Verify get_product_shipping_info and get_product_sku_details on sync and async clients."""
    with _make_sync_client() as sync_client:
        sync_ship = sync_client.get_product_shipping_info(
            product_id=live_data.product_id,
            sku_id=live_data.sku_id,
            ship_to_country="US",
            target_sale_price=live_data.target_sale_price,
            target_currency=Currency.USD,
            target_language=Language.EN,
            tax_rate=live_data.tax_rate,
        )
        assert isinstance(sync_ship, ProductShippingInfo)
        assert sync_ship.delivery_days is not None
        assert isinstance(sync_ship.shipping_fee_decimal, Decimal)
        _throttle()

        sync_sku = sync_client.get_product_sku_details(
            live_data.product_id,
            ship_to_country="US",
            need_deliver_info=True,
        )
        assert isinstance(sync_sku, ProductSkuDetail)
        assert sync_sku.product_id == live_data.product_id
        assert sync_sku.item_info is not None
        assert len(sync_sku.skus) > 0
        assert isinstance(sync_sku.skus[0].sku_id, int)
        assert isinstance(sync_sku.skus[0].sale_price_with_tax_decimal, Decimal)
        _throttle()

    async def _run_async() -> tuple[ProductShippingInfo, ProductSkuDetail]:
        async with _make_async_client() as async_client:
            a_ship = await async_client.get_product_shipping_info(
                product_id=live_data.product_id,
                sku_id=live_data.sku_id,
                ship_to_country="US",
                target_sale_price=live_data.target_sale_price,
                target_currency=Currency.USD,
                target_language=Language.EN,
                tax_rate=live_data.tax_rate,
            )
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_sku = await async_client.get_product_sku_details(
                live_data.product_id,
                ship_to_country="US",
                need_deliver_info=True,
            )
            return a_ship, a_sku

    async_ship, async_sku = asyncio.run(_run_async())
    assert async_ship.shipping_fee_decimal == sync_ship.shipping_fee_decimal
    assert async_ship.delivery_days == sync_ship.delivery_days
    assert async_sku.product_id == sync_sku.product_id
    assert len(async_sku.skus) == len(sync_sku.skus)
    _throttle()


def test_live_links_and_promotions_sync_and_async(
    live_data: DiscoveredLiveTestData,
) -> None:
    """Verify generate_affiliate_link, get_affiliate_links, and promotion.info.get methods."""
    with _make_sync_client() as sync_client:
        sync_link = sync_client.generate_affiliate_link(live_data.product_url)
        assert isinstance(sync_link, AffiliateLink)
        assert bool(sync_link.promotion_link)
        assert sync_link.promotion_link and sync_link.promotion_link.startswith(
            "https://s.click.aliexpress.com/"
        )
        assert sync_link.source_value == live_data.product_url
        _throttle()

        sync_links = sync_client.get_affiliate_links([live_data.product_url])
        assert isinstance(sync_links, list)
        assert len(sync_links) == 1
        assert sync_links[0].promotion_link and sync_links[0].promotion_link.startswith(
            "https://s.click.aliexpress.com/"
        )
        assert sync_links[0].source_value == sync_link.source_value
        assert sync_links[0].tracking_id == sync_link.tracking_id
        _throttle()

        # Batch promotion info returns list[ProductPromotionResult] (may be [] if no active coupon)
        sync_promos = sync_client.get_promotions_info([live_data.product_id])
        assert isinstance(sync_promos, list)
        _throttle()

        # Single promotion info returns ProductPromotionResult if product has coupons,
        # or raises ProductNotFoundError if the product has no active coupon promotions
        if sync_promos:
            single_promo = sync_client.get_promotion_info(live_data.product_id)
            assert isinstance(single_promo, ProductPromotionResult)
        else:
            with pytest.raises(ProductNotFoundError):
                sync_client.get_promotion_info(live_data.product_id)
        _throttle()

    async def _run_async() -> tuple[
        AffiliateLink, list[AffiliateLink], list[ProductPromotionResult]
    ]:
        async with _make_async_client() as async_client:
            a_link = await async_client.generate_affiliate_link(live_data.product_url)
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_links = await async_client.get_affiliate_links([live_data.product_url])
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_promos = await async_client.get_promotions_info([live_data.product_id])
            return a_link, a_links, a_promos

    async_link, async_links, async_promos = asyncio.run(_run_async())
    assert async_link.promotion_link and async_link.promotion_link.startswith(
        "https://s.click.aliexpress.com/"
    )
    assert async_link.source_value == sync_link.source_value
    assert async_link.tracking_id == sync_link.tracking_id
    assert len(async_links) == len(sync_links)
    assert len(async_promos) == len(sync_promos)
    _throttle()


def test_live_orders_list_and_index_sync_and_async(
    live_data: DiscoveredLiveTestData,
) -> None:
    """Verify get_order_list and get_order_list_by_index on sync and async clients."""
    with _make_sync_client() as sync_client:
        sync_page = sync_client.get_order_list(
            status=OrderStatus.PAYMENT_COMPLETED,
            start_time=live_data.order_start_time,
            end_time=live_data.order_end_time,
            page_size=20,
        )
        assert isinstance(sync_page, Page)
        _throttle()

        sync_cursor = sync_client.get_order_list_by_index(
            status=OrderStatus.PAYMENT_COMPLETED,
            start_time=live_data.order_start_time,
            end_time=live_data.order_end_time,
            page_size=20,
        )
        assert isinstance(sync_cursor, CursorPage)
        _throttle()

    async def _run_async() -> tuple[Page[Order], CursorPage[Order]]:
        async with _make_async_client() as async_client:
            a_page = await async_client.get_order_list(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time=live_data.order_start_time,
                end_time=live_data.order_end_time,
                page_size=20,
            )
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_cursor = await async_client.get_order_list_by_index(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time=live_data.order_start_time,
                end_time=live_data.order_end_time,
                page_size=20,
            )
            return a_page, a_cursor

    async_page, async_cursor = asyncio.run(_run_async())
    assert len(async_page.items) == len(sync_page.items)
    assert len(async_cursor.items) == len(sync_cursor.items)
    if sync_page.items:
        first_order = sync_page.items[0]
        assert isinstance(first_order, Order)
        assert isinstance(first_order.order_id, int)
        assert isinstance(first_order.paid_amount_decimal, Decimal)
        assert isinstance(first_order.created_datetime, datetime)
        assert async_page.items[0].order_id == first_order.order_id
    _throttle()


def test_live_order_details_sync_and_async(
    live_data: DiscoveredLiveTestData,
) -> None:
    """Verify get_order_details and get_orders_details with a real discovered sub_order_id."""
    if live_data.sub_order_id is None:
        pytest.skip(
            "No real orders found in the account over the past 6 months; "
            "skipping positive get_order_details test."
        )

    with _make_sync_client() as sync_client:
        sync_order = sync_client.get_order_details(live_data.sub_order_id)
        assert isinstance(sync_order, Order)
        assert sync_order.sub_order_id == live_data.sub_order_id
        assert isinstance(sync_order.paid_amount_decimal, Decimal)
        assert isinstance(sync_order.commission_rate_pct, Decimal)
        assert isinstance(sync_order.created_datetime, datetime)
        assert not hasattr(sync_order, "current_record_count")
        _throttle()

        sync_orders = sync_client.get_orders_details([live_data.sub_order_id])
        assert isinstance(sync_orders, list)
        assert len(sync_orders) == 1
        assert sync_orders[0].sub_order_id == live_data.sub_order_id
        _throttle()

    async def _run_async() -> tuple[Order, list[Order]]:
        async with _make_async_client() as async_client:
            a_order = await async_client.get_order_details(live_data.sub_order_id)  # type: ignore[arg-type]
            await asyncio.sleep(RATE_LIMIT_DELAY_SEC)
            a_orders = await async_client.get_orders_details([live_data.sub_order_id])  # type: ignore[list-item]
            return a_order, a_orders

    async_order, async_orders = asyncio.run(_run_async())
    assert async_order.sub_order_id == sync_order.sub_order_id
    assert async_order.paid_amount_decimal == sync_order.paid_amount_decimal
    assert len(async_orders) == 1
    _throttle()


def test_live_error_paths_and_secret_redaction() -> None:
    """Verify live error mapping for auth, signature, not-found, and validation errors."""
    app_secret = os.environ.get("ALIEXPRESS_APP_SECRET", "")

    # 1. Wrong app_secret -> SignatureError (live API returns code="IncompleteSignature")
    with AliExpressClient(
        app_secret="deliberately_wrong_secret_for_test",
        max_retries=2,
        backoff_factor=1.0,
    ) as bad_sig_client:
        assert "deliberately_wrong_secret_for_test" not in repr(bad_sig_client)
        with pytest.raises(SignatureError) as sig_exc:
            bad_sig_client.get_categories()
        assert "deliberately_wrong_secret_for_test" not in str(sig_exc.value)
        if app_secret:
            assert app_secret not in str(sig_exc.value)
    _throttle()

    # 2. Wrong app_key -> AuthenticationError (live API returns code="InvalidAppKey")
    with AliExpressClient(
        app_key="9999999999999999",
        app_secret="deliberately_wrong_secret_for_test",
        max_retries=2,
        backoff_factor=1.0,
    ) as bad_key_client:
        with pytest.raises(AuthenticationError) as auth_exc:
            bad_key_client.get_categories()
        assert auth_exc.value.code == "InvalidAppKey"
    _throttle()

    with _make_sync_client() as client:
        # 3. Nonexistent product_id -> ProductNotFoundError
        with pytest.raises(ProductNotFoundError) as prod_nf:
            client.get_product_details(999999999999999999)
        assert prod_nf.value.product_id == "999999999999999999"
        _throttle()

        # 4. Nonexistent order_id -> OrderNotFoundError
        with pytest.raises(OrderNotFoundError) as ord_nf:
            client.get_order_details(9999999999999999)
        assert ord_nf.value.order_id == "9999999999999999"
        _throttle()

        # 5. Nonexistent category_id -> CategoryNotFoundError
        with pytest.raises(CategoryNotFoundError) as cat_nf:
            client.get_category(999999999, use_cache=True)
        assert cat_nf.value.category_id == "999999999"

        # 6. Non-affiliate domain on generate_affiliate_link -> LinkGenerationError
        with pytest.raises(LinkGenerationError):
            client.generate_affiliate_link("https://example.com/not-aliexpress")
        _throttle()

        # 7. Invalid parameters -> ValidationError (local validation, no network needed)
        with pytest.raises(ValidationError):
            client.get_product_details("111,222")
        with pytest.raises(ValidationError):
            client.get_order_details("111,222")
        with pytest.raises(ValidationError):
            client.smart_match_products()
