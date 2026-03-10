"""Appraisal models for item price checking.

Pydantic models for parsing EVE item pastes and returning Jita market prices.
"""

from pydantic import BaseModel, Field


class AppraisalRequest(BaseModel):
    """Request containing raw pasted text from EVE Online."""

    raw_text: str = Field(
        ..., description="Raw text pasted from EVE Online inventory or manual entry"
    )


class AppraisalItem(BaseModel):
    """A single appraised item with market prices."""

    name: str = Field(..., description="Item type name")
    type_id: int = Field(..., description="EVE type ID")
    quantity: int = Field(..., description="Number of items")
    buy_price: float = Field(..., description="Jita best buy price per unit")
    sell_price: float = Field(..., description="Jita lowest sell price per unit")
    buy_total: float = Field(..., description="Total buy value (buy_price * quantity)")
    sell_total: float = Field(
        ..., description="Total sell value (sell_price * quantity)"
    )


class AppraisalResponse(BaseModel):
    """Full appraisal result with all items and totals."""

    items: list[AppraisalItem] = Field(
        default_factory=list, description="Appraised items"
    )
    total_buy: float = Field(0.0, description="Sum of all buy totals")
    total_sell: float = Field(0.0, description="Sum of all sell totals")
    unknown_items: list[str] = Field(
        default_factory=list,
        description="Item names that could not be resolved to type IDs",
    )
    item_count: int = Field(0, description="Number of resolved items")
