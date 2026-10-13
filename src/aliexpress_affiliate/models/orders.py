"""Pydantic v2 models for ``order.get``, ``order.list``, and ``order.listbyindex``."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Union

from pydantic import Field, field_validator, model_validator

from ..utils import unwrap_xml_list
from .common import (
    AliExpressBaseModel,
    AliExpressRequestModel,
    CursorPage,
    OrderStatus,
    OrderTimeType,
    Page,
    PaginatedResult,
    parse_optional_datetime,
    parse_optional_decimal,
    parse_yn_bool,
)


class GetOrderInfoRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.order.get``."""

    order_ids: str = Field(..., alias="order_ids")
    fields: Optional[str] = Field(default=None, alias="fields")
    app_signature: Optional[str] = Field(default=None, alias="app_signature")


class GetOrderListRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.order.list``."""

    start_time: str = Field(..., alias="start_time")
    end_time: str = Field(..., alias="end_time")
    status: Union[OrderStatus, str] = Field(..., alias="status")
    time_type: Optional[Union[OrderTimeType, str]] = Field(default=None, alias="time_type")
    fields: Optional[str] = Field(default=None, alias="fields")
    locale_site: Optional[str] = Field(default=None, alias="locale_site")
    page_no: Optional[int] = Field(default=None, alias="page_no", ge=1)
    page_size: Optional[int] = Field(default=None, alias="page_size", ge=1, le=50)
    app_signature: Optional[str] = Field(default=None, alias="app_signature")


class GetOrderListByIndexRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.order.listbyindex``."""

    start_time: str = Field(..., alias="start_time")
    end_time: str = Field(..., alias="end_time")
    status: Union[OrderStatus, str] = Field(..., alias="status")
    time_type: Optional[Union[OrderTimeType, str]] = Field(default=None, alias="time_type")
    start_query_index_id: Optional[str] = Field(default=None, alias="start_query_index_id")
    fields: Optional[str] = Field(default=None, alias="fields")
    page_size: Optional[int] = Field(default=None, alias="page_size", ge=1, le=50)
    app_signature: Optional[str] = Field(default=None, alias="app_signature")


class Order(AliExpressBaseModel):
    """Affiliate order record returned by ``order.get``, ``order.list``, and ``order.listbyindex``.

    Note:
        - AliExpress returns ``customer_parameters`` in ``order.get`` and ``custom_parameters``
          in ``order.list`` / ``order.listbyindex``. This model normalizes both to
          :attr:`custom_parameters` and exposes :attr:`customer_parameters` as a property alias.
        - In ``order.list`` and ``order.listbyindex``, :attr:`order_id` is the parent order ID
          while :attr:`sub_order_id` (and :attr:`order_number`) is the line-item sub-order ID
          accepted by ``aliexpress.affiliate.order.get`` (:meth:`get_order_details`).
        - Timestamps and amounts are also exposed via typed :class:`datetime`, :class:`Decimal`,
          and :class:`bool` properties.
    """

    order_id: Optional[int] = Field(default=None, alias="order_id")
    sub_order_id: Optional[int] = Field(default=None, alias="sub_order_id")
    order_number: Optional[int] = Field(default=None, alias="order_number")
    parent_order_number: Optional[int] = Field(default=None, alias="parent_order_number")
    order_status: Optional[str] = Field(default=None, alias="order_status")
    effect_detail_status: Optional[str] = Field(default=None, alias="effect_detail_status")
    order_platform: Optional[str] = Field(default=None, alias="order_platform")
    order_type: Optional[str] = Field(default=None, alias="order_type")
    tracking_id: Optional[str] = Field(default=None, alias="tracking_id")

    product_id: Optional[int] = Field(default=None, alias="product_id")
    product_title: Optional[str] = Field(default=None, alias="product_title")
    product_detail_url: Optional[str] = Field(default=None, alias="product_detail_url")
    product_main_image_url: Optional[str] = Field(default=None, alias="product_main_image_url")
    product_count: Optional[int] = Field(default=None, alias="product_count")
    category_id: Optional[int] = Field(default=None, alias="category_id")

    paid_amount: Optional[str] = Field(default=None, alias="paid_amount")
    paid_time: Optional[str] = Field(default=None, alias="paid_time")
    estimated_paid_commission: Optional[str] = Field(
        default=None, alias="estimated_paid_commission"
    )
    finished_amount: Optional[str] = Field(default=None, alias="finished_amount")
    finished_time: Optional[str] = Field(default=None, alias="finished_time")
    estimated_finished_commission: Optional[str] = Field(
        default=None, alias="estimated_finished_commission"
    )
    completed_settlement_time: Optional[str] = Field(
        default=None, alias="completed_settlement_time"
    )
    created_time: Optional[str] = Field(default=None, alias="created_time")

    commission_rate: Optional[str] = Field(default=None, alias="commission_rate")
    incentive_commission_rate: Optional[str] = Field(
        default=None, alias="incentive_commission_rate"
    )
    estimated_incentive_paid_commission: Optional[str] = Field(
        default=None, alias="estimated_incentive_paid_commission"
    )
    estimated_incentive_finished_commission: Optional[str] = Field(
        default=None, alias="estimated_incentive_finished_commission"
    )
    new_buyer_bonus_commission: Optional[str] = Field(
        default=None, alias="new_buyer_bonus_commission"
    )

    settled_currency: Optional[str] = Field(default=None, alias="settled_currency")
    ship_to_country: Optional[str] = Field(default=None, alias="ship_to_country")
    is_hot_product: Optional[str] = Field(default=None, alias="is_hot_product")
    is_new_buyer: Optional[str] = Field(default=None, alias="is_new_buyer")
    is_affiliate_product: Optional[str] = Field(default=None, alias="is_affiliate_product")
    custom_parameters: Optional[str] = Field(default=None, alias="custom_parameters")

    @model_validator(mode="before")
    @classmethod
    def _normalize_custom_parameters(cls, data: Any) -> Any:
        if (
            isinstance(data, dict)
            and "custom_parameters" not in data
            and "customer_parameters" in data
        ):
            copied = dict(data)
            copied["custom_parameters"] = copied["customer_parameters"]
            return copied
        return data

    @field_validator(
        "paid_amount",
        "estimated_paid_commission",
        "finished_amount",
        "estimated_finished_commission",
        "estimated_incentive_paid_commission",
        "estimated_incentive_finished_commission",
        "new_buyer_bonus_commission",
        mode="before",
    )
    @classmethod
    def _coerce_numeric_to_str(cls, value: Any) -> Optional[str]:
        if value is None or value == "":
            return None
        return str(value)

    @property
    def id(self) -> Optional[int]:
        """Clean alias for :attr:`order_id`."""
        return self.order_id

    @property
    def customer_parameters(self) -> Optional[str]:
        """Alias for :attr:`custom_parameters` (returned as ``customer_parameters`` by ``order.get``)."""
        return self.custom_parameters

    @property
    def is_hot_product_bool(self) -> Optional[bool]:
        """Boolean representation of :attr:`is_hot_product` (``'Y'`` -> ``True``, ``'N'`` -> ``False``)."""
        return parse_yn_bool(self.is_hot_product)

    @property
    def is_new_buyer_bool(self) -> Optional[bool]:
        """Boolean representation of :attr:`is_new_buyer` (``'Y'`` -> ``True``, ``'N'`` -> ``False``)."""
        return parse_yn_bool(self.is_new_buyer)

    @property
    def is_affiliate_product_bool(self) -> Optional[bool]:
        """Boolean representation of :attr:`is_affiliate_product` (``'Y'`` -> ``True``, ``'N'`` -> ``False``)."""
        return parse_yn_bool(self.is_affiliate_product)

    @property
    def paid_amount_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`paid_amount`."""
        return parse_optional_decimal(self.paid_amount)

    @property
    def finished_amount_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`finished_amount`."""
        return parse_optional_decimal(self.finished_amount)

    @property
    def estimated_paid_commission_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`estimated_paid_commission`."""
        return parse_optional_decimal(self.estimated_paid_commission)

    @property
    def estimated_finished_commission_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`estimated_finished_commission`."""
        return parse_optional_decimal(self.estimated_finished_commission)

    @property
    def estimated_incentive_paid_commission_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`estimated_incentive_paid_commission`."""
        return parse_optional_decimal(self.estimated_incentive_paid_commission)

    @property
    def estimated_incentive_finished_commission_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`estimated_incentive_finished_commission`."""
        return parse_optional_decimal(self.estimated_incentive_finished_commission)

    @property
    def new_buyer_bonus_commission_decimal(self) -> Optional[Decimal]:
        """Parsed :class:`Decimal` for :attr:`new_buyer_bonus_commission`."""
        return parse_optional_decimal(self.new_buyer_bonus_commission)

    @property
    def commission_rate_pct(self) -> Optional[Decimal]:
        """Parsed percentage :class:`Decimal` for :attr:`commission_rate`."""
        return parse_optional_decimal(self.commission_rate)

    @property
    def incentive_commission_rate_pct(self) -> Optional[Decimal]:
        """Parsed percentage :class:`Decimal` for :attr:`incentive_commission_rate`."""
        return parse_optional_decimal(self.incentive_commission_rate)

    @property
    def paid_datetime(self) -> Optional[datetime]:
        """Parsed :class:`datetime` for :attr:`paid_time`."""
        return parse_optional_datetime(self.paid_time)

    @property
    def created_datetime(self) -> Optional[datetime]:
        """Parsed :class:`datetime` for :attr:`created_time`."""
        return parse_optional_datetime(self.created_time)

    @property
    def finished_datetime(self) -> Optional[datetime]:
        """Parsed :class:`datetime` for :attr:`finished_time`."""
        return parse_optional_datetime(self.finished_time)

    @property
    def completed_settlement_datetime(self) -> Optional[datetime]:
        """Parsed :class:`datetime` for :attr:`completed_settlement_time`."""
        return parse_optional_datetime(self.completed_settlement_time)


class OrderInfoResponse(AliExpressBaseModel):
    """Internal API envelope for ``aliexpress.affiliate.order.get``."""

    current_record_count: int = Field(default=0, alias="current_record_count")
    orders: list[Order] = Field(default_factory=list, alias="orders")

    @field_validator("orders", mode="before")
    @classmethod
    def _unwrap_orders(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "order")


class OrderListResponse(PaginatedResult):
    """Internal API envelope for ``aliexpress.affiliate.order.list``."""

    orders: list[Order] = Field(default_factory=list, alias="orders")

    @field_validator("orders", mode="before")
    @classmethod
    def _unwrap_orders(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "order")

    def to_page(
        self,
        *,
        requested_page_no: Optional[int] = None,
        requested_page_size: Optional[int] = None,
    ) -> Page[Order]:
        """Convert this raw API envelope into a clean :class:`Page[Order]`."""
        return Page[Order](
            items=self.orders,
            page_no=self.current_page_no if self.current_page_no is not None else requested_page_no,
            page_size=(
                requested_page_size
                if requested_page_size is not None
                else (self.current_record_count or len(self.orders))
            ),
            total_count=self.total_record_count,
            total_pages=self.total_page_no,
        )


class OrderListByIndexResponse(AliExpressBaseModel):
    """Internal API envelope for ``aliexpress.affiliate.order.listbyindex``."""

    current_record_count: int = Field(default=0, alias="current_record_count")
    min_query_index_id: Optional[str] = Field(default=None, alias="min_query_index_id")
    max_query_index_id: Optional[str] = Field(default=None, alias="max_query_index_id")
    orders: list[Order] = Field(default_factory=list, alias="orders")

    @field_validator("orders", mode="before")
    @classmethod
    def _unwrap_orders(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "order")

    def to_cursor_page(
        self,
        *,
        requested_page_size: Optional[int] = None,
    ) -> CursorPage[Order]:
        """Convert this raw API envelope into a clean :class:`CursorPage[Order]`."""
        return CursorPage[Order](
            items=self.orders,
            min_query_index_id=self.min_query_index_id,
            max_query_index_id=self.max_query_index_id,
            page_size=(
                requested_page_size
                if requested_page_size is not None
                else (self.current_record_count or len(self.orders))
            ),
        )
