"""Orders resource (``order.get``, ``order.list``, and ``order.listbyindex``)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Union

from ..exceptions import OrderNotFoundError, ResourceNotFoundError
from ..models.common import CursorPage, LocaleSite, OrderStatus, OrderTimeType, Page
from ..models.orders import (
    GetOrderInfoRequest,
    GetOrderListByIndexRequest,
    GetOrderListRequest,
    Order,
    OrderInfoResponse,
    OrderListByIndexResponse,
    OrderListResponse,
)
from ..utils import format_csv_param, normalize_order_ids, validate_single_order_id
from .base import AsyncResource, SyncResource

__all__ = [
    "API_ORDER_GET",
    "API_ORDER_LIST",
    "API_ORDER_LIST_BY_INDEX",
    "AsyncOrdersResource",
    "OrdersResource",
]

API_ORDER_GET: str = "aliexpress.affiliate.order.get"
API_ORDER_LIST: str = "aliexpress.affiliate.order.list"
API_ORDER_LIST_BY_INDEX: str = "aliexpress.affiliate.order.listbyindex"


class _OrdersMixin:
    """Shared request builders and response unwrappers for order endpoints."""

    def _build_order_get_request(
        self,
        order_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> GetOrderInfoRequest:
        csv_ids = normalize_order_ids(order_ids)
        return GetOrderInfoRequest(
            order_ids=csv_ids,
            fields=format_csv_param(fields),
            app_signature=app_signature,
        )

    def _build_order_list_request(
        self,
        *,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        locale_site: Optional[Union[LocaleSite, str]] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> GetOrderListRequest:
        site_val = locale_site.value if isinstance(locale_site, LocaleSite) else locale_site
        return GetOrderListRequest(
            start_time=start_time,
            end_time=end_time,
            status=status,
            time_type=time_type,
            fields=format_csv_param(fields),
            locale_site=site_val,
            page_no=page_no,
            page_size=page_size,
            app_signature=app_signature,
        )

    def _build_order_list_by_index_request(
        self,
        *,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        start_query_index_id: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> GetOrderListByIndexRequest:
        return GetOrderListByIndexRequest(
            start_time=start_time,
            end_time=end_time,
            status=status,
            time_type=time_type,
            start_query_index_id=start_query_index_id,
            fields=format_csv_param(fields),
            page_size=page_size,
            app_signature=app_signature,
        )

    @staticmethod
    def _unwrap_single_order(envelope: OrderInfoResponse, single_id: str) -> Order:
        if not envelope.orders:
            raise OrderNotFoundError(single_id)
        return envelope.orders[0]

    @staticmethod
    def _unwrap_batch_orders(
        envelope: OrderInfoResponse,
        *,
        raise_on_empty: bool,
    ) -> list[Order]:
        if raise_on_empty and not envelope.orders:
            raise OrderNotFoundError(message="No orders found for the specified order_ids")
        return envelope.orders

    @staticmethod
    def _handle_batch_orders_not_found(
        exc: ResourceNotFoundError,
        *,
        raise_on_empty: bool,
    ) -> list[Order]:
        if raise_on_empty:
            raise OrderNotFoundError(
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return []

    @staticmethod
    def _empty_order_page(
        page_no: Optional[int],
        page_size: Optional[int],
        *,
        raise_on_empty: bool,
    ) -> Page[Order]:
        if raise_on_empty:
            raise
        return Page[Order](
            items=[],
            page_no=page_no or 1,
            page_size=page_size or 0,
            total_count=0,
            total_pages=0,
        )

    @staticmethod
    def _finalize_order_page(
        envelope: OrderListResponse,
        *,
        page_no: Optional[int],
        page_size: Optional[int],
        raise_on_empty: bool,
    ) -> Page[Order]:
        if raise_on_empty and not envelope.orders:
            raise ResourceNotFoundError("No orders found for the specified parameters")
        return envelope.to_page(requested_page_no=page_no, requested_page_size=page_size)

    @staticmethod
    def _empty_order_cursor_page(
        page_size: Optional[int],
        *,
        raise_on_empty: bool,
    ) -> CursorPage[Order]:
        if raise_on_empty:
            raise
        return CursorPage[Order](items=[], page_size=page_size or 0)

    @staticmethod
    def _finalize_order_cursor_page(
        envelope: OrderListByIndexResponse,
        *,
        page_size: Optional[int],
        raise_on_empty: bool,
    ) -> CursorPage[Order]:
        if raise_on_empty and not envelope.orders:
            raise ResourceNotFoundError("No orders found for the specified parameters")
        return envelope.to_cursor_page(requested_page_size=page_size)


class OrdersResource(SyncResource, _OrdersMixin):
    """Synchronous resource for ``order.get``, ``order.list``, and ``order.listbyindex``."""

    def get_detail(
        self,
        order_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> Order:
        """Retrieve a single affiliate order by its order or sub-order ID (``aliexpress.affiliate.order.get``).

        Unwraps the API envelope internally so pagination/record-count metadata never leaks.

        Args:
            order_id: Single order or sub-order ID (``int`` or numeric ``str``).
            fields: Optional response field list.
            app_signature: Optional API signature parameter.

        Returns:
            Single :class:`Order` domain model.

        Raises:
            ValidationError: If ``order_id`` is empty, non-numeric, a sequence, or comma-separated.
            OrderNotFoundError: If no order is returned for ``order_id``.

        Example:
            ```python
            order = client.orders.get_detail(3000000000010001)
            print(order.order_id, order.order_status, order.paid_amount)
            ```
        """
        single_id = validate_single_order_id(order_id)
        req = self._build_order_get_request(
            single_id,
            fields=fields,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_ORDER_GET, req.to_api_params(), OrderInfoResponse
            )
        except ResourceNotFoundError as exc:
            raise OrderNotFoundError(
                single_id,
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return self._unwrap_single_order(envelope, single_id)

    get = get_detail

    def get_details(
        self,
        order_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> list[Order]:
        """Batch retrieve affiliate orders by multiple order or sub-order IDs (``aliexpress.affiliate.order.get``).

        Args:
            order_ids: Comma-separated string, integer, or sequence of order/sub-order IDs.
            fields: Optional response field list.
            app_signature: Optional API signature parameter.

        Returns:
            List of :class:`Order` domain models.

        Raises:
            ValidationError: If ``order_ids`` is empty or contains invalid order IDs.
            OrderNotFoundError: If ``raise_on_empty=True`` and no orders are returned.

        Example:
            ```python
            orders = client.orders.get_details([3000000000010001, 3000000000010002])
            for order in orders:
                print(order.order_id, order.order_status, order.paid_amount)
            ```
        """
        req = self._build_order_get_request(
            order_ids,
            fields=fields,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_ORDER_GET, req.to_api_params(), OrderInfoResponse
            )
        except ResourceNotFoundError as exc:
            return self._handle_batch_orders_not_found(
                exc, raise_on_empty=self.config.raise_on_empty
            )
        return self._unwrap_batch_orders(envelope, raise_on_empty=self.config.raise_on_empty)

    def list(
        self,
        *,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        locale_site: Optional[Union[LocaleSite, str]] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Order]:
        """Retrieve a paginated list of affiliate orders (``aliexpress.affiliate.order.list``).

        Args:
            status: Order status filter (e.g. ``OrderStatus.PAYMENT_COMPLETED`` or ``"Payment Completed"``).
            start_time: Start time in PST format ``"YYYY-MM-DD HH:MM:SS"``.
            end_time: End time in PST format ``"YYYY-MM-DD HH:MM:SS"``.
            time_type: Optional time type (``Payment Completed Time``, ``Buyer Confirmed Receipt Time``,
                or ``Completed Settlement Time``).
            fields: Optional response field list.
            locale_site: Optional site filter (``"global"``, ``"ru_site"``, ``"es_site"``, ``"it_site"``).
            page_no: Page number (>= 1).
            page_size: Records per page (1 to 50).
            app_signature: Optional API signature parameter.

        Returns:
            Typed :class:`Page[Order]` containing ``items``, ``page_no``, ``page_size``,
            ``total_count``, ``total_pages``, and ``has_next``.

        Example:
            ```python
            orders_page = client.orders.list(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-07 23:59:59",
                page_size=50,
            )
            for order in orders_page.items:
                print(order.order_id, order.sub_order_id, order.paid_amount)
            ```
        """
        req = self._build_order_list_request(
            status=status,
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            fields=fields,
            locale_site=locale_site,
            page_no=page_no,
            page_size=page_size,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_ORDER_LIST, req.to_api_params(), OrderListResponse
            )
        except ResourceNotFoundError:
            return self._empty_order_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_order_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    def list_by_index(
        self,
        *,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        start_query_index_id: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> CursorPage[Order]:
        """Retrieve affiliate orders using cursor/index pagination (``aliexpress.affiliate.order.listbyindex``).

        Args:
            status: Order status filter (e.g. ``OrderStatus.PAYMENT_COMPLETED``).
            start_time: Start time in PST format ``"YYYY-MM-DD HH:MM:SS"``.
            end_time: End time in PST format ``"YYYY-MM-DD HH:MM:SS"``.
            time_type: Optional time type filter.
            start_query_index_id: Cursor index ID from a previous response's ``max_query_index_id``
                (if omitted, fetches the first page).
            fields: Optional response field list.
            page_size: Records per page (1 to 50).
            app_signature: Optional API signature parameter.

        Returns:
            Typed :class:`CursorPage[Order]` with ``items``, ``min_query_index_id``,
            ``max_query_index_id``, ``page_size``, and ``has_next``.

        Example:
            ```python
            page1 = client.orders.list_by_index(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-07 23:59:59",
            )
            if page1.has_next:
                page2 = client.orders.list_by_index(
                    status=OrderStatus.PAYMENT_COMPLETED,
                    start_time="2026-01-01 00:00:00",
                    end_time="2026-01-07 23:59:59",
                    start_query_index_id=page1.max_query_index_id,
                )
            ```
        """
        req = self._build_order_list_by_index_request(
            status=status,
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            start_query_index_id=start_query_index_id,
            fields=fields,
            page_size=page_size,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = self._transport.request_model(
                API_ORDER_LIST_BY_INDEX, req.to_api_params(), OrderListByIndexResponse
            )
        except ResourceNotFoundError:
            return self._empty_order_cursor_page(
                page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_order_cursor_page(
            envelope, page_size=page_size, raise_on_empty=self.config.raise_on_empty
        )


class AsyncOrdersResource(AsyncResource, _OrdersMixin):
    """Asynchronous resource for ``order.get``, ``order.list``, and ``order.listbyindex``."""

    async def get_detail(
        self,
        order_id: Union[str, int],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> Order:
        """Asynchronously retrieve a single affiliate order by its order or sub-order ID (``aliexpress.affiliate.order.get``).

        Raises:
            ValidationError: If ``order_id`` is empty, non-numeric, a sequence, or comma-separated.
            OrderNotFoundError: If no order is returned for ``order_id``.

        Example:
            ```python
            order = await async_client.orders.get_detail(3000000000010001)
            ```
        """
        single_id = validate_single_order_id(order_id)
        req = self._build_order_get_request(
            single_id,
            fields=fields,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_ORDER_GET, req.to_api_params(), OrderInfoResponse
            )
        except ResourceNotFoundError as exc:
            raise OrderNotFoundError(
                single_id,
                message=exc.message,
                code=exc.code,
                sub_code=exc.sub_code,
                sub_msg=exc.sub_msg,
                request_id=exc.request_id,
                raw_response=exc.raw_response,
            ) from exc
        return self._unwrap_single_order(envelope, single_id)

    get = get_detail

    async def get_details(
        self,
        order_ids: Union[str, int, Sequence[Union[str, int]]],
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        app_signature: Optional[str] = None,
    ) -> list[Order]:
        """Asynchronously batch retrieve affiliate orders by multiple order or sub-order IDs.

        Example:
            ```python
            orders = await async_client.orders.get_details([3000000000010001, 3000000000010002])
            ```
        """
        req = self._build_order_get_request(
            order_ids,
            fields=fields,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_ORDER_GET, req.to_api_params(), OrderInfoResponse
            )
        except ResourceNotFoundError as exc:
            return self._handle_batch_orders_not_found(
                exc, raise_on_empty=self.config.raise_on_empty
            )
        return self._unwrap_batch_orders(envelope, raise_on_empty=self.config.raise_on_empty)

    async def list(
        self,
        *,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        locale_site: Optional[Union[LocaleSite, str]] = None,
        page_no: Optional[int] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> Page[Order]:
        """Asynchronously retrieve a paginated list of affiliate orders (``aliexpress.affiliate.order.list``).

        Example:
            ```python
            orders_page = await async_client.orders.list(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-07 23:59:59",
            )
            ```
        """
        req = self._build_order_list_request(
            status=status,
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            fields=fields,
            locale_site=locale_site,
            page_no=page_no,
            page_size=page_size,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_ORDER_LIST, req.to_api_params(), OrderListResponse
            )
        except ResourceNotFoundError:
            return self._empty_order_page(
                page_no, page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_order_page(
            envelope,
            page_no=page_no,
            page_size=page_size,
            raise_on_empty=self.config.raise_on_empty,
        )

    async def list_by_index(
        self,
        *,
        status: Union[OrderStatus, str],
        start_time: str,
        end_time: str,
        time_type: Optional[Union[OrderTimeType, str]] = None,
        start_query_index_id: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        page_size: Optional[int] = None,
        app_signature: Optional[str] = None,
    ) -> CursorPage[Order]:
        """Asynchronously retrieve affiliate orders using cursor/index pagination (``aliexpress.affiliate.order.listbyindex``).

        Example:
            ```python
            page = await async_client.orders.list_by_index(
                status=OrderStatus.PAYMENT_COMPLETED,
                start_time="2026-01-01 00:00:00",
                end_time="2026-01-07 23:59:59",
            )
            ```
        """
        req = self._build_order_list_by_index_request(
            status=status,
            start_time=start_time,
            end_time=end_time,
            time_type=time_type,
            start_query_index_id=start_query_index_id,
            fields=fields,
            page_size=page_size,
            app_signature=self._resolve_app_signature(app_signature),
        )
        try:
            envelope = await self._transport.request_model(
                API_ORDER_LIST_BY_INDEX, req.to_api_params(), OrderListByIndexResponse
            )
        except ResourceNotFoundError:
            return self._empty_order_cursor_page(
                page_size, raise_on_empty=self.config.raise_on_empty
            )
        return self._finalize_order_cursor_page(
            envelope, page_size=page_size, raise_on_empty=self.config.raise_on_empty
        )
