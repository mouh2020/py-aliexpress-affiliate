"""Categories resource (``aliexpress.affiliate.category.get``)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Union

from ..exceptions import CategoryNotFoundError, ResourceNotFoundError, ValidationError
from ..models.categories import CategoriesResponse, Category, ChildCategory, GetCategoriesRequest
from .base import AsyncResource, SyncResource

__all__ = [
    "API_CATEGORY_GET",
    "AsyncCategoriesResource",
    "CategoriesResource",
    "filter_child_categories",
    "filter_parent_categories",
]

API_CATEGORY_GET: str = "aliexpress.affiliate.category.get"


def _parse_category_id(category_id: Union[int, str], param_name: str = "category_id") -> int:
    """Validate and convert ``category_id`` to a positive integer."""
    if isinstance(category_id, bool):
        raise ValidationError(f"Parameter '{param_name}' must be an int or numeric string")
    if isinstance(category_id, int):
        if category_id <= 0:
            raise ValidationError(f"Parameter '{param_name}' must be a positive integer")
        return category_id
    if isinstance(category_id, str):
        stripped = category_id.strip()
        if stripped.isdigit() and int(stripped) > 0:
            return int(stripped)
    raise ValidationError(
        f"Parameter '{param_name}' must be a single positive integer, got {category_id!r}"
    )


def filter_parent_categories(categories: Sequence[Category]) -> list[Category]:
    """Filter a sequence of :class:`Category` objects to top-level parent categories."""
    return [cat for cat in categories if cat.is_parent]


def filter_child_categories(
    categories: Sequence[Category],
    parent_category_id: Union[int, str],
) -> list[ChildCategory]:
    """Filter a sequence of :class:`Category` objects to children of ``parent_category_id``."""
    parent_id = _parse_category_id(parent_category_id, "parent_category_id")
    return [
        ChildCategory.model_validate(cat.model_dump(by_alias=True))
        for cat in categories
        if cat.parent_category_id == parent_id
    ]


class _CategoriesMixin:
    """Shared request builder and category filtering helpers for sync and async resources."""

    _cached_categories: Optional[list[Category]]

    def _build_categories_request(
        self, app_signature: Optional[str] = None
    ) -> GetCategoriesRequest:
        return GetCategoriesRequest(app_signature=app_signature)

    def _finalize_categories_list(
        self,
        envelope: CategoriesResponse,
        *,
        raise_on_empty: bool,
    ) -> list[Category]:
        if raise_on_empty and not envelope.categories:
            raise CategoryNotFoundError(message="No categories returned by AliExpress API")
        self._cached_categories = envelope.categories
        return envelope.categories

    @staticmethod
    def _find_category_by_id(
        categories: list[Category],
        target_id: int,
    ) -> Category:
        for cat in categories:
            if cat.category_id == target_id:
                return cat
        raise CategoryNotFoundError(target_id)

    @staticmethod
    def _filter_parents(
        categories: list[Category],
        *,
        raise_on_empty: bool,
    ) -> list[Category]:
        parents = filter_parent_categories(categories)
        if raise_on_empty and not parents:
            raise CategoryNotFoundError(message="No parent categories found")
        return parents

    @staticmethod
    def _filter_children(
        categories: list[Category],
        parent_id: int,
        *,
        raise_on_empty: bool,
    ) -> list[ChildCategory]:
        children = filter_child_categories(categories, parent_id)
        if raise_on_empty and not children:
            raise CategoryNotFoundError(
                parent_id,
                message=f"No child categories found for parent_category_id={parent_id}",
            )
        return children


class CategoriesResource(SyncResource, _CategoriesMixin):
    """Synchronous resource for ``aliexpress.affiliate.category.get``."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._cached_categories: Optional[list[Category]] = None

    def get_categories(
        self,
        *,
        app_signature: Optional[str] = None,
    ) -> list[Category]:
        """Retrieve all available affiliate categories (parent and child).

        Calls ``aliexpress.affiliate.category.get`` and caches the result on this resource
        instance for optional reuse by :meth:`get_detail`, :meth:`get_parent_categories`,
        and :meth:`get_child_categories`.

        Args:
            app_signature: Optional API signature parameter.

        Returns:
            List of :class:`Category` models.

        Raises:
            CategoryNotFoundError: If ``raise_on_empty=True`` and no categories are returned.
            APIError: If the API returns a gateway or business error.

        Example:
            ```python
            categories = client.categories.get_categories()
            for cat in categories[:5]:
                print(cat.category_id, cat.category_name, cat.is_parent)
            ```
        """
        req = self._build_categories_request(self._resolve_app_signature(app_signature))
        try:
            envelope = self._transport.request_model(
                API_CATEGORY_GET, req.to_api_params(), CategoriesResponse
            )
        except ResourceNotFoundError as exc:
            if self.config.raise_on_empty:
                raise CategoryNotFoundError(message=exc.message) from exc
            self._cached_categories = []
            return []
        return self._finalize_categories_list(envelope, raise_on_empty=self.config.raise_on_empty)

    def _get_or_fetch(
        self,
        *,
        use_cache: bool,
        app_signature: Optional[str],
    ) -> list[Category]:
        if use_cache and self._cached_categories is not None:
            return self._cached_categories
        return self.get_categories(app_signature=app_signature)

    def get_detail(
        self,
        category_id: Union[int, str],
        *,
        use_cache: bool = True,
        app_signature: Optional[str] = None,
    ) -> Category:
        """Retrieve a single :class:`Category` by its ``category_id``.

        Args:
            category_id: Single numeric category ID (``int`` or ``str``).
            use_cache: Reuse previously fetched categories if available (defaults to ``True``).
            app_signature: Optional API signature parameter.

        Returns:
            Single :class:`Category` model matching ``category_id``.

        Raises:
            ValidationError: If ``category_id`` is not a single positive integer.
            CategoryNotFoundError: If no category with ``category_id`` exists.

        Example:
            ```python
            cat = client.categories.get_detail(200000345)
            print(cat.category_id, cat.category_name)
            ```
        """
        target_id = _parse_category_id(category_id, "category_id")
        categories = self._get_or_fetch(use_cache=use_cache, app_signature=app_signature)
        return self._find_category_by_id(categories, target_id)

    get = get_detail

    def get_parent_categories(
        self,
        use_cache: bool = True,
        *,
        app_signature: Optional[str] = None,
    ) -> list[Category]:
        """Retrieve all top-level parent categories (categories with ``parent_category_id is None``).

        Args:
            use_cache: Reuse previously fetched categories if available (defaults to ``True``).
            app_signature: Optional API signature parameter.

        Returns:
            List of top-level :class:`Category` models.

        Example:
            ```python
            parents = client.categories.get_parent_categories()
            ```
        """
        categories = self._get_or_fetch(use_cache=use_cache, app_signature=app_signature)
        return self._filter_parents(categories, raise_on_empty=self.config.raise_on_empty)

    def get_child_categories(
        self,
        parent_category_id: Union[int, str],
        use_cache: bool = True,
        *,
        app_signature: Optional[str] = None,
    ) -> list[ChildCategory]:
        """Retrieve all child categories belonging to ``parent_category_id``.

        Args:
            parent_category_id: Parent category ID to filter by.
            use_cache: Reuse previously fetched categories if available (defaults to ``True``).
            app_signature: Optional API signature parameter.

        Returns:
            List of :class:`ChildCategory` models whose ``parent_category_id`` matches.

        Example:
            ```python
            children = client.categories.get_child_categories(200000345)
            ```
        """
        parent_id = _parse_category_id(parent_category_id, "parent_category_id")
        categories = self._get_or_fetch(use_cache=use_cache, app_signature=app_signature)
        return self._filter_children(
            categories, parent_id, raise_on_empty=self.config.raise_on_empty
        )

    list = get_categories


class AsyncCategoriesResource(AsyncResource, _CategoriesMixin):
    """Asynchronous resource for ``aliexpress.affiliate.category.get``."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._cached_categories: Optional[list[Category]] = None

    async def get_categories(
        self,
        *,
        app_signature: Optional[str] = None,
    ) -> list[Category]:
        """Asynchronously retrieve all available affiliate categories (parent and child).

        Args:
            app_signature: Optional API signature parameter.

        Returns:
            List of :class:`Category` models.

        Example:
            ```python
            categories = await async_client.categories.get_categories()
            ```
        """
        req = self._build_categories_request(self._resolve_app_signature(app_signature))
        try:
            envelope = await self._transport.request_model(
                API_CATEGORY_GET, req.to_api_params(), CategoriesResponse
            )
        except ResourceNotFoundError as exc:
            if self.config.raise_on_empty:
                raise CategoryNotFoundError(message=exc.message) from exc
            self._cached_categories = []
            return []
        return self._finalize_categories_list(envelope, raise_on_empty=self.config.raise_on_empty)

    async def _get_or_fetch(
        self,
        *,
        use_cache: bool,
        app_signature: Optional[str],
    ) -> list[Category]:
        if use_cache and self._cached_categories is not None:
            return self._cached_categories
        return await self.get_categories(app_signature=app_signature)

    async def get_detail(
        self,
        category_id: Union[int, str],
        *,
        use_cache: bool = True,
        app_signature: Optional[str] = None,
    ) -> Category:
        """Asynchronously retrieve a single :class:`Category` by its ``category_id``.

        Args:
            category_id: Single numeric category ID (``int`` or ``str``).
            use_cache: Reuse previously fetched categories if available (defaults to ``True``).
            app_signature: Optional API signature parameter.

        Returns:
            Single :class:`Category` model matching ``category_id``.

        Raises:
            ValidationError: If ``category_id`` is not a single positive integer.
            CategoryNotFoundError: If no category with ``category_id`` exists.

        Example:
            ```python
            cat = await async_client.categories.get_detail(200000345)
            ```
        """
        target_id = _parse_category_id(category_id, "category_id")
        categories = await self._get_or_fetch(use_cache=use_cache, app_signature=app_signature)
        return self._find_category_by_id(categories, target_id)

    get = get_detail

    async def get_parent_categories(
        self,
        use_cache: bool = True,
        *,
        app_signature: Optional[str] = None,
    ) -> list[Category]:
        """Asynchronously retrieve all top-level parent categories.

        Example:
            ```python
            parents = await async_client.categories.get_parent_categories()
            ```
        """
        categories = await self._get_or_fetch(use_cache=use_cache, app_signature=app_signature)
        return self._filter_parents(categories, raise_on_empty=self.config.raise_on_empty)

    async def get_child_categories(
        self,
        parent_category_id: Union[int, str],
        use_cache: bool = True,
        *,
        app_signature: Optional[str] = None,
    ) -> list[ChildCategory]:
        """Asynchronously retrieve all child categories belonging to ``parent_category_id``.

        Example:
            ```python
            children = await async_client.categories.get_child_categories(200000345)
            ```
        """
        parent_id = _parse_category_id(parent_category_id, "parent_category_id")
        categories = await self._get_or_fetch(use_cache=use_cache, app_signature=app_signature)
        return self._filter_children(
            categories, parent_id, raise_on_empty=self.config.raise_on_empty
        )

    list = get_categories
