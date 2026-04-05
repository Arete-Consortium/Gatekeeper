"""Market arbitrage models for cross-hub price comparison.

Pydantic models for comparing market prices across EVE trade hubs
and identifying profitable arbitrage opportunities.
"""

from pydantic import BaseModel, Field


class HubPriceData(BaseModel):
    """Market price data for a single trade hub."""

    system_id: int = Field(..., description="Trade hub solar system ID")
    system_name: str = Field(..., description="Trade hub name")
    region_id: int = Field(..., description="Region ID containing the hub")
    best_buy: float = Field(0.0, description="Highest buy order price")
    best_sell: float = Field(0.0, description="Lowest sell order price")
    spread: float = Field(0.0, description="Spread percentage between best sell and best buy")
    buy_volume: int = Field(0, description="Total buy order volume")
    sell_volume: int = Field(0, description="Total sell order volume")


class ArbitrageOpportunity(BaseModel):
    """A profitable trade between two hubs."""

    buy_hub: str = Field(..., description="Hub to buy from (lowest sell)")
    buy_hub_id: int = Field(..., description="Buy hub system ID")
    buy_price: float = Field(..., description="Buy price per unit")
    sell_hub: str = Field(..., description="Hub to sell at (highest buy)")
    sell_hub_id: int = Field(..., description="Sell hub system ID")
    sell_price: float = Field(..., description="Sell price per unit")
    profit_per_unit: float = Field(..., description="ISK profit per unit")
    margin_pct: float = Field(..., description="Profit margin percentage")


class ArbitrageCompareResponse(BaseModel):
    """Full arbitrage comparison result across trade hubs."""

    type_id: int = Field(..., description="EVE type ID")
    type_name: str = Field("", description="Item type name")
    hubs: list[HubPriceData] = Field(default_factory=list, description="Price data per hub")
    opportunities: list[ArbitrageOpportunity] = Field(
        default_factory=list, description="Arbitrage opportunities sorted by margin"
    )


class PopularItem(BaseModel):
    """A commonly traded item for quick lookup."""

    type_id: int = Field(..., description="EVE type ID")
    name: str = Field(..., description="Item name")
    category: str = Field(..., description="Item category")


class PopularItemsResponse(BaseModel):
    """List of commonly traded items."""

    items: list[PopularItem] = Field(default_factory=list, description="Popular items")
    count: int = Field(0, description="Number of items")
