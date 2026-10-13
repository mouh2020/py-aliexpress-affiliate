# Changelog

All notable changes to `py-aliexpress-affiliate` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-10-13

### Fixed
- **Live SKU details unwrapping (`aliexpress.affiliate.product.sku.detail.get`)**: Added support for the `"traffic_sku_info_list"` inner list key returned inside `"ae_item_sku_info"` by the live AliExpress gateway (alongside `"ae_item_sku_info_d_t_o"` and `"sku_info"`).
- **Live empty-result error codes (`ERROR-405` / `405`)**: Mapped gateway `code="15"` with `sub_code="ERROR-405"` / `"405"` (`"The result is empty"`) and business `resp_code=405` to `ResourceNotFoundError`, converting single-item lookups (`get_product_details`, `get_order_details`, `get_product_sku_details`, `get_product_shipping_info`, `get_promotion_info`) into `ProductNotFoundError` / `OrderNotFoundError` and returning empty `list` / `Page` / `CursorPage` for list/batch queries when `raise_on_empty=False`.
- **String-typed TOP error codes**: Mapped `"IncompleteSignature"` and `"InvalidSignature"` to `SignatureError`, `"InvalidAppKey"` and `"InvalidAccessToken"` to `AuthenticationError`, and `"ApiCallLimit"` to `RateLimitError`.
- **Automatic retry on gateway `ApiCallLimit`**: Both `SyncTransport` and `AsyncTransport` now automatically retry with exponential backoff and freshly signed timestamps when the gateway returns `error_response.code == "ApiCallLimit"` and `max_retries > 0`.
- **Order incentive commission `Decimal` properties**: Added `Order.estimated_incentive_paid_commission_decimal`, `Order.estimated_incentive_finished_commission_decimal`, and `Order.new_buyer_bonus_commission_decimal` (with numeric-to-string coercion on `Order`).

### Changed
- **Transport secret redaction**: Hardened `SyncTransport` and `AsyncTransport` so sensitive query parameters (`app_key`, `sign`, `session`, `tracking_id`) and secrets are scrubbed from any `httpx.HTTPError` logs or `NetworkError` messages.
- **Deduplicated resource mixins & packaging**: Consolidated shared response unwrapping across `_CategoriesMixin`, `_LinksMixin`, `_ProductsMixin`, `_OrdersMixin`, `_PromotionsMixin`, and `_BaseClientMixin`; configured single-source dynamic versioning and clean `sdist` packaging in `pyproject.toml`.

## [0.2.0] - 2026-10-13

### Breaking Changes
- **`get_product_details(product_id)`** (and `client.products.get_detail(product_id)`):
  - Now accepts **exactly ONE** `product_id: str | int` (or single AliExpress product URL) and returns a **single `Product`** model (not `list[Product]`).
  - Raises `ProductNotFoundError` (subclass of `ResourceNotFoundError` and `AliExpressError`) if no product is returned for `product_id`.
  - Raises `ValidationError` if a list or comma-separated multi-ID string is passed.
  - **Migration**: Use `get_products_details(product_ids)` (or `client.products.get_details(product_ids)`) for batch lookups returning `list[Product]`.
- **`get_order_details(order_id)`** (and `client.orders.get_detail(order_id)`):
  - Now accepts **exactly ONE** `order_id: str | int` and returns a **single `Order`** model instead of `OrderInfoResponse`.
  - Unwraps the API envelope internally (`current_record_count` and `orders` never leak).
  - Raises `OrderNotFoundError` if no order is returned for `order_id`.
  - **Migration**: Use `get_orders_details(order_ids)` (or `client.orders.get_details(order_ids)`) for batch lookups returning `list[Order]`.
- **`get_order_list(...)`** (and `client.orders.list(...)`):
  - Returns a typed `Page[Order]` (`items`, `page_no`, `page_size`, `total_count`, `total_pages`, `has_next`) instead of `OrderListResponse`.
- **`get_order_list_by_index(...)`** (and `client.orders.list_by_index(...)`):
  - Returns a typed `CursorPage[Order]` (`items`, `min_query_index_id`, `max_query_index_id`, `page_size`, `has_next`) instead of `OrderListByIndexResponse`.
- **`get_products(...)`, `get_hot_products(...)`, `download_hot_products(...)`, `smart_match_products(...)`, `get_featured_promo_products(...)`**:
  - All paginated product endpoints now return `Page[Product]` instead of raw `ProductsResponse` / `HotProductsResponse` / `FeaturedPromoProductsResponse` envelopes.
  - Note: `Page[Product]` implements `__iter__`, `__len__`, `__getitem__`, and exposes `.products` as a compatibility alias for `.items`.
- **`get_featured_promos(...)`**:
  - Returns `list[FeaturedPromo]` directly instead of `FeaturedPromosResponse`.
- **`get_promotion_info(product_id)`** vs **`get_promotions_info(product_ids)`**:
  - `get_promotion_info(product_id)` now accepts a single `product_id` and returns a single `ProductPromotionResult` (or raises `ProductNotFoundError`).
  - Added `get_promotions_info(product_ids)` for batch lookups (up to 10 product IDs) returning `list[ProductPromotionResult]`.

### Added
- `Page[T]` and `CursorPage[T]` generic pagination models with `items`, `page_no`, `page_size`, `total_count`, `total_pages`, and `has_next`.
- Single-item convenience methods `generate_affiliate_link(source_value) -> AffiliateLink` and `get_category(category_id) -> Category`.
- `LinkGenerationError` for single-URL affiliate link generation failures.
- Typed `Decimal`, `datetime`, and `bool` properties on `Product`, `PromoCodeInfo`, `Order`, `ProductShippingInfo`, `SkuItemInfo`, `SkuVariantInfo`, and `ProductPromotion`.

## [0.1.0] - 2026-10-13

### Added
- Initial release covering all 15 AliExpress Affiliate API methods (`sync` and `async` clients), TOP MD5 request signing, Pydantic v2 models, custom exception hierarchy, and `respx` unit tests.
