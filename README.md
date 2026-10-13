# 🛍️ py-aliexpress-affiliate

[![PyPI version](https://img.shields.io/pypi/v/py-aliexpress-affiliate.svg)](https://pypi.org/project/py-aliexpress-affiliate/)
[![CI](https://github.com/mouh2020/py-aliexpress-affiliate/actions/workflows/ci.yml/badge.svg)](https://github.com/mouh2020/py-aliexpress-affiliate/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Typed](https://img.shields.io/badge/typing-strict-brightgreen.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **Disclaimer**: `py-aliexpress-affiliate` is an **unofficial**, independent open-source community library. It is **not affiliated with, endorsed by, or sponsored by AliExpress or Alibaba Group**. "AliExpress" and "Alibaba" are trademarks of Alibaba Group Holding Limited.

A production-quality, **fully typed** (`mypy --strict`) Python library that wraps all **15 official AliExpress Affiliate (AE Affiliate) Open Platform API endpoints** with both **synchronous** and **asynchronous** (`httpx`) clients and **Pydantic v2** domain models.

---

## ✨ Features

- 🎯 **Complete AE Affiliate API Coverage (15/15 Endpoints)**:
  - 🔗 Links (`aliexpress.affiliate.link.generate`)
  - 🗂️ Categories (`aliexpress.affiliate.category.get` + parent/child filtering & caching)
  - 🎉 Featured Promotions (`featuredpromo.get`, `featuredpromo.products.get`)
  - 📦 Products & Hot Products (`product.query`, `hotproduct.query`, `hotproduct.download`, `productdetail.get`, `product.smartmatch`)
  - 🚚 Shipping & SKU Details (`product.shipping.get`, `product.sku.detail.get`)
  - 🎟️ Real-time Coupons & Promotions (`promotion.info.get`)
  - 🧾 Orders (`order.get`, `order.list`, `order.listbyindex`)
- 🧩 **Clean Domain Return Types**:
  - **Single-item methods** (`get_product_details`, `get_order_details`, `generate_affiliate_link`, `get_category`, `get_product_shipping_info`, `get_product_sku_details`, `get_promotion_info`) accept a single identifier and return a single domain model (or raise `ProductNotFoundError`, `OrderNotFoundError`, `CategoryNotFoundError`, `LinkGenerationError`).
  - **Batch methods** (`get_products_details`, `get_orders_details`, `get_affiliate_links`, `get_promotions_info`) accept sequences of identifiers and return `list[Model]`.
  - **Paginated list methods** (`get_products`, `get_hot_products`, `download_hot_products`, `get_featured_promo_products`, `smart_match_products`, `get_order_list`, `get_order_list_by_index`) return generic `Page[Model]` or `CursorPage[Model]` containers (`items`, `page_no`, `page_size`, `total_count`, `total_pages`, `has_next`).
- 🔐 **Exact TOP Request Signing**: Preserves the battle-tested TOP MD5 signing algorithm from [`sergioteula/python-aliexpress-api`](https://github.com/sergioteula/python-aliexpress-api).
- ⚡ **Sync & Async Parity**: `AliExpressClient` and `AsyncAliExpressClient` expose identical methods and resource namespaces (`.links`, `.categories`, `.products`, `.orders`, `.promotions`).
- 🛡️ **Reliability & Security by Default**: Configurable timeouts, exponential backoff retries (including automatic retry on transient `ApiCallLimit` gateway rate limits), and automatic redaction of secrets (`app_secret`, `session`, `app_signature`) in `repr()`, `str()`, transport exception messages, and debug logs.

---

## 📦 Installation

```bash
pip install py-aliexpress-affiliate
```

For development:

```bash
pip install -e ".[dev]"
```

---

## ⚙️ Configuration

You can pass credentials and defaults directly to `AliExpressClient` / `AsyncAliExpressClient` or configure them via environment variables:

| Constructor Arg | Environment Variable | Default | Description |
|---|---|---|---|
| `app_key` | `ALIEXPRESS_APP_KEY` | *(Required)* | AliExpress Open Platform App Key |
| `app_secret` | `ALIEXPRESS_APP_SECRET` | *(Required)* | AliExpress Open Platform App Secret (redacted in `repr`) |
| `tracking_id` | `ALIEXPRESS_TRACKING_ID` | `None` | Default affiliate tracking ID |
| `language` | `ALIEXPRESS_LANGUAGE` | `"EN"` | Target language (`Language.EN`, `"ES"`, etc.) |
| `currency` | `ALIEXPRESS_CURRENCY` | `"USD"` | Target currency (`Currency.USD`, `"EUR"`, etc.) |
| `country` | `ALIEXPRESS_COUNTRY` | `None` | Default destination country (`"US"`, `"DE"`, etc.) |
| `app_signature` | `ALIEXPRESS_APP_SIGNATURE` | `None` | Optional legacy API signature (redacted in `repr`) |
| `session` | `ALIEXPRESS_SESSION` | `None` | Optional TOP session token (redacted in `repr`) |
| `base_url` | `ALIEXPRESS_BASE_URL` | `"https://api-sg.aliexpress.com"` | AliExpress TOP Gateway URL |

---

## 🚀 Quickstart

### 🔄 Synchronous Usage

```python
from aliexpress_affiliate import (
    AliExpressClient,
    Currency,
    Language,
    LinkType,
    OrderStatus,
    SortBy,
)

with AliExpressClient(
    app_key="YOUR_APP_KEY",
    app_secret="YOUR_APP_SECRET",
    tracking_id="default",
    language=Language.EN,
    currency=Currency.USD,
    country="US",
) as client:
    # 1. Single-item lookup: returns ONE Product (or raises ProductNotFoundError)
    product = client.get_product_details("1005004757833857")
    print(product.id, product.title, product.target_sale_price_decimal)

    # 2. Batch lookup: returns list[Product]
    products = client.get_products_details(
        ["1005004757833857", "https://www.aliexpress.com/item/33006951782.html"]
    )

    # 3. Generate a single affiliate link: returns ONE AffiliateLink
    link = client.generate_affiliate_link(
        "https://www.aliexpress.com/item/1005004757833857.html",
        promotion_link_type=LinkType.NORMAL,
    )
    print("Affiliate link:", link.promotion_link)

    # 4. Paginated product search: returns Page[Product]
    page = client.get_products(
        keywords="mechanical keyboard",
        sort=SortBy.LAST_VOLUME_DESC,
        page_no=1,
        page_size=10,
    )
    print(f"Page {page.page_no}/{page.total_pages} (total={page.total_count}, has_next={page.has_next})")
    for item in page.items:
        print(item.id, item.title, item.target_sale_price, item.latest_volume)

    # 5. Single order lookup by sub_order_id: returns ONE Order (or raises OrderNotFoundError)
    order = client.get_order_details(3000000000010001)
    print(order.order_id, order.sub_order_id, order.order_status, order.paid_amount_decimal)

    # 6. Paginated order list: returns Page[Order]
    order_page = client.get_order_list(
        status=OrderStatus.PAYMENT_COMPLETED,
        start_time="2026-01-01 00:00:00",
        end_time="2026-01-07 23:59:59",
        page_no=1,
        page_size=50,
    )
    for o in order_page.items:
        print(o.order_id, o.sub_order_id, o.paid_amount_decimal, o.estimated_paid_commission_decimal)
```

### ⚡ Asynchronous Usage

```python
import asyncio
from aliexpress_affiliate import AsyncAliExpressClient, Currency, Language

async def main() -> None:
    async with AsyncAliExpressClient(
        app_key="YOUR_APP_KEY",
        app_secret="YOUR_APP_SECRET",
        tracking_id="default",
        language=Language.EN,
        currency=Currency.EUR,
        country="DE",
    ) as client:
        categories, hot_page = await asyncio.gather(
            client.get_parent_categories(),
            client.get_hot_products(keywords="earbuds", page_size=5),
        )
        print(f"Loaded {len(categories)} parent categories and {len(hot_page.items)} hot products")

asyncio.run(main())
```

---

## 📚 API Reference

Both `AliExpressClient` and `AsyncAliExpressClient` expose top-level methods as well as grouped resource namespaces (`client.links`, `client.categories`, `client.products`, `client.promotions`, `client.orders`):

| AliExpress Method | Single-Item Method -> Return Type | Batch / List Method -> Return Type |
|---|---|---|
| `aliexpress.affiliate.link.generate` | `generate_affiliate_link(url)` -> `AffiliateLink` | `get_affiliate_links(urls)` -> `list[AffiliateLink]` |
| `aliexpress.affiliate.category.get` | `get_category(category_id)` -> `Category` | `get_categories()` -> `list[Category]`<br>`get_parent_categories()` -> `list[Category]`<br>`get_child_categories(parent_id)` -> `list[ChildCategory]` |
| `aliexpress.affiliate.featuredpromo.get` | — | `get_featured_promos()` -> `list[FeaturedPromo]` |
| `aliexpress.affiliate.featuredpromo.products.get` | — | `get_featured_promo_products(...)` -> `Page[Product]` |
| `aliexpress.affiliate.hotproduct.download` | — | `download_hot_products(category_id, ...)` -> `Page[Product]` |
| `aliexpress.affiliate.hotproduct.query` | — | `get_hot_products(...)` -> `Page[Product]` |
| `aliexpress.affiliate.product.query` | — | `get_products(...)` -> `Page[Product]` |
| `aliexpress.affiliate.productdetail.get` | `get_product_details(product_id)` -> `Product` | `get_products_details(product_ids)` -> `list[Product]` |
| `aliexpress.affiliate.product.smartmatch` | — | `smart_match_products(...)` -> `Page[Product]` |
| `aliexpress.affiliate.product.shipping.get` | `get_product_shipping_info(...)` -> `ProductShippingInfo` | — |
| `aliexpress.affiliate.product.sku.detail.get` | `get_product_sku_details(product_id)` -> `ProductSkuDetail` | — |
| `aliexpress.affiliate.promotion.info.get` | `get_promotion_info(product_id)` -> `ProductPromotionResult` | `get_promotions_info(product_ids)` -> `list[ProductPromotionResult]` |
| `aliexpress.affiliate.order.get` | `get_order_details(order_id)` -> `Order` *(by `sub_order_id`)* | `get_orders_details(order_ids)` -> `list[Order]` |
| `aliexpress.affiliate.order.list` | — | `get_order_list(...)` -> `Page[Order]` |
| `aliexpress.affiliate.order.listbyindex` | — | `get_order_list_by_index(...)` -> `CursorPage[Order]` |

---

## 🚨 Error Handling

All exceptions inherit from `AliExpressError`:

- `AliExpressError`
  - `ConfigurationError` — Missing or invalid `app_key`, `app_secret`, or client settings.
  - `ValidationError` — Invalid method arguments, passing multiple IDs to a single-item method, or unparseable URLs.
  - `NetworkError` — HTTP transport failure, timeout, or non-200 status after retries.
  - `APIError` — Gateway (`error_response`) or business-level (`resp_code != 200`) API error.
    - `AuthenticationError` — Invalid `app_key` (`code="29"` or `"InvalidAppKey"`), session token, HTTP 401/403, or insufficient API permissions.
      - `SignatureError` — Invalid TOP request signature (`code="25"`, `"IncompleteSignature"`, or `"InvalidSignature"`).
    - `RateLimitError` — QPS or call frequency quota exceeded (`code="7"`, `"ApiCallLimit"`, or HTTP `429`).
    - `ResourceNotFoundError` — Base exception for missing resources (`ERROR-405` / `405`) or empty queries when `raise_on_empty=True`.
      - `ProductNotFoundError` — Raised when `get_product_details`, `get_product_sku_details`, `get_product_shipping_info`, or `get_promotion_info` finds no matching product.
      - `OrderNotFoundError` — Raised when `get_order_details` finds no matching order.
      - `CategoryNotFoundError` — Raised when `get_category` finds no matching category.
    - `LinkGenerationError` — Raised when `generate_affiliate_link` fails to produce a promotion URL.

```python
from aliexpress_affiliate import (
    AliExpressClient,
    APIError,
    AuthenticationError,
    NetworkError,
    OrderNotFoundError,
    ProductNotFoundError,
    RateLimitError,
    SignatureError,
    ValidationError,
)

try:
    with AliExpressClient() as client:
        product = client.get_product_details("33006951782")
        order = client.get_order_details(3000000000010001)
except ProductNotFoundError as exc:
    print(f"Product {exc.product_id} was not found")
except OrderNotFoundError as exc:
    print(f"Order {exc.order_id} was not found")
except SignatureError as exc:
    print(f"Signature mismatch: {exc.message} (request_id={exc.request_id})")
except AuthenticationError as exc:
    print(f"Auth failed: {exc.code} - {exc.sub_msg}")
except RateLimitError as exc:
    print(f"Rate limited: {exc}")
except APIError as exc:
    print(f"API error [{exc.code}]: {exc.message}")
except NetworkError as exc:
    print(f"Transport error (HTTP {exc.status_code}): {exc.message}")
except ValidationError as exc:
    print(f"Invalid input: {exc.message}")
```

---

## 📜 Attribution, Trademarks & License

Released under the [MIT License](LICENSE).
- 🙏 The TOP MD5 request-signing logic and legacy compatibility aliases are adapted from [`sergioteula/python-aliexpress-api`](https://github.com/sergioteula/python-aliexpress-api) (Copyright (c) 2020 Sergio Abad, MIT License).
- ⚖️ **Non-Affiliation Notice**: This project is an independent, unofficial open-source library and is not affiliated with, endorsed by, or sponsored by AliExpress or Alibaba Group Holding Limited.