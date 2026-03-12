"""Market ticker models for real-time price tracking.

Pydantic models for ESI market history data across major trade hub regions.
"""

from pydantic import BaseModel, Field


class MarketTickerItem(BaseModel):
    """A single market ticker entry for an item in a region."""

    type_id: int = Field(..., description="EVE type ID")
    type_name: str = Field(..., description="Item type name")
    region_id: int = Field(..., description="Region ID")
    region_name: str = Field(..., description="Region name")
    average_price: float = Field(..., description="Average price for the day")
    highest: float = Field(..., description="Highest price for the day")
    lowest: float = Field(..., description="Lowest price for the day")
    volume: int = Field(..., description="Total volume traded")
    date: str = Field(..., description="Date of the market data (YYYY-MM-DD)")
    price_change_pct: float = Field(0.0, description="Price change percentage vs previous day")


class MarketTickerResponse(BaseModel):
    """Response containing all tracked market ticker items."""

    items: list[MarketTickerItem] = Field(default_factory=list, description="Market ticker entries")
    item_count: int = Field(0, description="Number of ticker items")


class MarketTickerHistoryResponse(BaseModel):
    """Response containing market history for a specific item across regions."""

    type_id: int = Field(..., description="EVE type ID")
    type_name: str = Field(..., description="Item type name")
    history: list[MarketTickerItem] = Field(
        default_factory=list, description="Historical market data"
    )
