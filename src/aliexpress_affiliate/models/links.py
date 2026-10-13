"""Pydantic v2 models for ``aliexpress.affiliate.link.generate``."""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import Field, field_validator

from ..utils import unwrap_xml_list
from .common import AliExpressBaseModel, AliExpressRequestModel, LinkType


class GenerateAffiliateLinksRequest(AliExpressRequestModel):
    """Request parameters for ``aliexpress.affiliate.link.generate``."""

    source_values: str = Field(..., alias="source_values")
    promotion_link_type: Union[LinkType, int] = Field(
        default=LinkType.NORMAL, alias="promotion_link_type"
    )
    tracking_id: str = Field(..., alias="tracking_id")
    ship_to_country: Optional[str] = Field(default=None, alias="ship_to_country")
    app_signature: Optional[str] = Field(default=None, alias="app_signature")


class AffiliateLink(AliExpressBaseModel):
    """Single generated affiliate promotion link item.

    Attributes:
        promotion_link: Generated AliExpress affiliate link (``http://s.click.aliexpress.com/...``).
        source_value: Original source URL or identifier submitted in the request.
        message: Optional explanation message if link generation failed for a specific item.
        tracking_id: Optional tracking ID associated with the generated link.
    """

    promotion_link: Optional[str] = Field(default=None, alias="promotion_link")
    source_value: str = Field(..., alias="source_value")
    message: Optional[str] = Field(default=None, alias="message")
    tracking_id: Optional[str] = Field(default=None, alias="tracking_id")

    @property
    def url(self) -> Optional[str]:
        """Clean alias for :attr:`promotion_link`."""
        return self.promotion_link


class AffiliateLinksResponse(AliExpressBaseModel):
    """Internal API envelope for ``aliexpress.affiliate.link.generate``."""

    total_result_count: int = Field(default=0, alias="total_result_count")
    tracking_id: Optional[str] = Field(default=None, alias="tracking_id")
    promotion_links: list[AffiliateLink] = Field(default_factory=list, alias="promotion_links")

    @field_validator("promotion_links", mode="before")
    @classmethod
    def _unwrap_promotion_links(cls, value: Any) -> list[Any]:
        return unwrap_xml_list(value, "promotion_link")

    @property
    def links(self) -> list[AffiliateLink]:
        """Clean alias for :attr:`promotion_links`."""
        return self.promotion_links
