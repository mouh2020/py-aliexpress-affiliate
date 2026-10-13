"""Common base Pydantic v2 models, generic pagination containers, and enumerations."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum, IntEnum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


def parse_optional_decimal(value: Optional[str]) -> Optional[Decimal]:
    """Parse an optional numeric or currency string (e.g. ``'15.90'`` or ``'5.00 USD'``) into :class:`Decimal`.

    Args:
        value: Raw string from the AliExpress API.

    Returns:
        Parsed :class:`Decimal`, or ``None`` if ``value`` is empty or non-numeric.
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    token = cleaned.split()[0].rstrip("%").strip()
    if not token:
        return None
    try:
        return Decimal(token)
    except (InvalidOperation, ValueError):
        return None


def parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an optional AliExpress timestamp string (``YYYY-MM-DD HH:MM:SS`` or ISO-8601) into :class:`datetime`.

    Args:
        value: Raw timestamp string from the AliExpress API.

    Returns:
        Parsed :class:`datetime`, or ``None`` if ``value`` is empty or unparseable.
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def parse_yn_bool(value: Optional[str]) -> Optional[bool]:
    """Parse an AliExpress ``'Y'`` / ``'N'`` or ``'true'`` / ``'false'`` flag into ``bool``."""
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if normalized in ("Y", "YES", "TRUE", "1"):
        return True
    if normalized in ("N", "NO", "FALSE", "0"):
        return False
    return None


class AliExpressBaseModel(BaseModel):
    """Base Pydantic v2 model for all AliExpress Affiliate response objects.

    Configures ``populate_by_name=True`` so models can be instantiated or accessed using
    either clean Python attribute names or AliExpress's raw snake_case aliases, and
    ``extra="allow"`` on responses so newly added AliExpress fields never break parsing.
    Also normalizes empty strings ``""`` to ``None`` for non-string fields so XML-to-JSON
    empty tags never fail integer/boolean validation.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        str_strip_whitespace=False,
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_strings_for_non_str_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if value == "":
                cleaned[key] = None
            else:
                cleaned[key] = value
        return cleaned


class AliExpressRequestModel(BaseModel):
    """Base Pydantic v2 model for API request parameters."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        use_enum_values=True,
    )

    def to_api_params(self) -> dict[str, Any]:
        """Serialize request model fields into non-``None`` AliExpress API parameter dictionary.

        Returns:
            Dictionary keyed by AliExpress API parameter aliases with ``None`` values omitted.
        """
        dumped = self.model_dump(by_alias=True, exclude_none=True)
        result: dict[str, Any] = {}
        for key, value in dumped.items():
            if isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result


class Page(AliExpressBaseModel, Generic[T]):
    """Typed paginated result container for list-style AliExpress Affiliate queries.

    Unwraps raw API pagination envelopes into clean, consistent attributes while preserving
    iteration support and backwards-compatible property aliases.

    Attributes:
        items: List of domain models on the current page.
        page_no: Current 1-based page number (if returned or requested).
        page_size: Requested page size or record count on the current page.
        total_count: Total matching records across all pages (if provided by the endpoint).
        total_pages: Total number of pages available (if provided by the endpoint).
        is_finished: Whether the stream of pages has finished (if provided by the endpoint).
    """

    items: list[T] = Field(default_factory=list)
    page_no: Optional[int] = Field(default=None)
    page_size: Optional[int] = Field(default=None)
    total_count: Optional[int] = Field(default=None)
    total_pages: Optional[int] = Field(default=None)
    is_finished: Optional[bool] = Field(default=None)

    @property
    def has_next(self) -> bool:
        """Return ``True`` if another page of results is likely available."""
        if self.is_finished is not None:
            return not self.is_finished
        if self.page_no is not None and self.total_pages is not None:
            return self.page_no < self.total_pages
        if (
            self.page_no is not None
            and self.page_size is not None
            and self.total_count is not None
            and self.page_size > 0
        ):
            return (self.page_no * self.page_size) < self.total_count
        return False

    @property
    def current_record_count(self) -> int:
        """Number of items on the current page."""
        return len(self.items)

    @property
    def current_page_no(self) -> Optional[int]:
        """Backwards-compatible alias for :attr:`page_no`."""
        return self.page_no

    @property
    def total_record_count(self) -> Optional[int]:
        """Backwards-compatible alias for :attr:`total_count`."""
        return self.total_count

    @property
    def total_page_no(self) -> Optional[int]:
        """Backwards-compatible alias for :attr:`total_pages`."""
        return self.total_pages

    @property
    def products(self) -> list[T]:
        """Convenience alias for :attr:`items` on product pages."""
        return self.items

    @property
    def orders(self) -> list[T]:
        """Convenience alias for :attr:`items` on order pages."""
        return self.items

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        return iter(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]


class CursorPage(AliExpressBaseModel, Generic[T]):
    """Typed cursor-paginated result container for index-based queries (``order.listbyindex``).

    Attributes:
        items: List of domain models on the current page.
        min_query_index_id: First cursor index ID in the returned batch.
        max_query_index_id: Last cursor index ID in the returned batch (pass as
            ``start_query_index_id`` to fetch the next page).
        page_size: Requested page size (if specified).
    """

    items: list[T] = Field(default_factory=list)
    min_query_index_id: Optional[str] = Field(default=None)
    max_query_index_id: Optional[str] = Field(default=None)
    page_size: Optional[int] = Field(default=None)

    @property
    def has_next(self) -> bool:
        """Return ``True`` if ``max_query_index_id`` is present and ``items`` is non-empty."""
        return bool(self.max_query_index_id and self.items)

    @property
    def current_record_count(self) -> int:
        """Number of items in the current batch."""
        return len(self.items)

    @property
    def orders(self) -> list[T]:
        """Convenience alias for :attr:`items` on cursor-paginated order batches."""
        return self.items

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        return iter(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]


class Currency(str, Enum):
    """Supported target currencies in the AliExpress Affiliate API."""

    USD = "USD"
    GBP = "GBP"
    CAD = "CAD"
    EUR = "EUR"
    UAH = "UAH"
    MXN = "MXN"
    TRY = "TRY"
    RUB = "RUB"
    BRL = "BRL"
    AUD = "AUD"
    INR = "INR"
    JPY = "JPY"
    IDR = "IDR"
    SEK = "SEK"
    KRW = "KRW"
    ILS = "ILS"
    THB = "THB"
    CLP = "CLP"
    VND = "VND"


class Language(str, Enum):
    """Supported target languages in the AliExpress Affiliate API."""

    EN = "EN"
    RU = "RU"
    PT = "PT"
    ES = "ES"
    FR = "FR"
    ID = "ID"
    IT = "IT"
    TH = "TH"
    JA = "JA"
    AR = "AR"
    VI = "VI"
    TR = "TR"
    DE = "DE"
    HE = "HE"
    KO = "KO"
    NL = "NL"
    PL = "PL"
    MX = "MX"
    CL = "CL"
    IW = "IW"
    IN = "IN"
    UK = "UK"


class ProductType(str, Enum):
    """Platform product type filter for product and hotproduct queries."""

    ALL = "ALL"
    PLAZA = "PLAZA"
    TMALL = "TMALL"


class SortBy(str, Enum):
    """Sort order values for ``aliexpress.affiliate.product.query`` and ``hotproduct.query``."""

    SALE_PRICE_ASC = "SALE_PRICE_ASC"
    SALE_PRICE_DESC = "SALE_PRICE_DESC"
    LAST_VOLUME_ASC = "LAST_VOLUME_ASC"
    LAST_VOLUME_DESC = "LAST_VOLUME_DESC"


class FeaturedPromoSortBy(str, Enum):
    """Sort order values for ``aliexpress.affiliate.featuredpromo.products.get``."""

    COMMISSION_ASC = "commissionAsc"
    COMMISSION_DESC = "commissionDesc"
    PRICE_ASC = "priceAsc"
    PRICE_DESC = "priceDesc"
    VOLUME_ASC = "volumeAsc"
    VOLUME_DESC = "volumeDesc"
    DISCOUNT_ASC = "discountAsc"
    DISCOUNT_DESC = "discountDesc"
    RATING_ASC = "ratingAsc"
    RATING_DESC = "ratingDesc"
    PROMOTION_TIME_ASC = "promotionTimeAsc"
    PROMOTION_TIME_DESC = "promotionTimeDesc"


class LinkType(IntEnum):
    """Promotion link type for ``aliexpress.affiliate.link.generate``."""

    NORMAL = 0
    HOTLINK = 2


class OrderStatus(str, Enum):
    """Order status filter for ``order.list`` and ``order.listbyindex``."""

    PAYMENT_COMPLETED = "Payment Completed"
    BUYER_CONFIRMED_RECEIPT = "Buyer Confirmed Receipt"
    COMPLETED_SETTLEMENT = "Completed Settlement"
    INVALID = "Invalid"


class OrderTimeType(str, Enum):
    """Time type filter for ``order.list`` and ``order.listbyindex``."""

    PAYMENT_COMPLETED_TIME = "Payment Completed Time"
    BUYER_CONFIRMED_RECEIPT_TIME = "Buyer Confirmed Receipt Time"
    COMPLETED_SETTLEMENT_TIME = "Completed Settlement Time"


class LocaleSite(str, Enum):
    """Locale site filter for ``hotproduct.download`` and ``order.list``."""

    GLOBAL = "global"
    IT_SITE = "it_site"
    ES_SITE = "es_site"
    RU_SITE = "ru_site"


class PaginatedResult(AliExpressBaseModel):
    """Internal raw pagination envelope returned by AliExpress Affiliate endpoints."""

    current_page_no: Optional[int] = None
    current_record_count: int = 0
    total_record_count: Optional[int] = None
    total_page_no: Optional[int] = None
