"""Common model types shared across domains."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class PriceRange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    min_price_cents: Optional[int] = None
    max_price_cents: Optional[int] = None
    tick_size_cents: Optional[int] = None
    min_price_dollars: Optional[str] = None
    max_price_dollars: Optional[str] = None
    tick_size_dollars: Optional[str] = None
