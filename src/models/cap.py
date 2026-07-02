from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CapOrderStatus(str, Enum):
    PENDING = "pending"
    NEGOTIATING = "negotiating"
    LOCKED = "locked"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CLEARING = "clearing"
    COMPLETED = "completed"
    FAILED = "failed"


class CapOrder(BaseModel):
    """An incoming order from the CAP network."""

    order_id: str = Field(..., description="Unique order ID")
    buyer_wallet: str = Field(..., description="Buyer's wallet address")
    agent_id: str = Field(..., description="Target agent ID")
    capability: str = Field(..., description="Requested capability/service")
    query_data: dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    status: CapOrderStatus = CapOrderStatus.PENDING
    price_usdc: Optional[float] = Field(None, description="Quoted price in USDC")
    created_at: str = Field(default="", description="ISO timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapDelivery(BaseModel):
    """Delivery payload submitted to the CAP network."""

    order_id: str
    agent_id: str
    report_json: dict[str, Any] = Field(description="Structured report output")
    report_markdown: str = Field(description="Human-readable report")
    hash_proof: str = Field(description="SHA-256 hash of delivery for verification")
    datasets_found: int = Field(default=0, description="Number of datasets returned")
    sources_searched: int = Field(default=0, description="Number of sources queried")
    execution_time_ms: int = Field(default=0, description="Total execution time")
    model_used: str = Field(default="", description="AI model used for query parsing")


class CapSettlement(BaseModel):
    """Settlement result after clear phase."""

    order_id: str
    payment_released: bool = Field(default=False)
    payment_amount_usdc: Optional[float] = None
    reputation_updated: bool = Field(default=False)
    pts_score: Optional[float] = Field(None, description="Updated Performance/Trust Score")
    settlement_tx: Optional[str] = Field(None, description="On-chain transaction hash")


class CapNegotiation(BaseModel):
    """Price estimation result for negotiation phase."""

    base_price_usdc: float = Field(default=0.01)
    source_count: int = Field(default=15)
    source_cost_usdc: float = Field(default=0.0)
    extras_cost_usdc: float = Field(default=0.0)
    total_price_usdc: float = Field(default=0.0)
    estimated_search_time_sec: int = Field(default=30)
    description: str = Field(default="")
