import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.cap.clear import process_clear
from src.cap.deliver import format_delivery, generate_hash_proof
from src.cap.negotiation import estimate_price
from src.groq.parser import QueryParser
from src.models.cap import CapOrder, CapOrderStatus
from src.models.query import ParsedQuery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DataScout API",
    description="Automated Dataset Search, Scoring & Reporting Agent on CROO Network",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-initialized singletons
_parser: QueryParser | None = None
_orders: dict[str, CapOrder] = {}


def get_parser() -> QueryParser:
    global _parser
    if _parser is None:
        _parser = QueryParser()
    return _parser


def _build_parsed_query(data: dict[str, Any]) -> ParsedQuery:
    """Construct a ParsedQuery from raw order query_data."""
    if "topic" in data:
        return ParsedQuery(
            topic=data["topic"],
            keywords=data.get("keywords", []),
            region=data.get("region"),
            domain=data.get("domain", "other"),
        )
    return ParsedQuery(topic="unknown", domain="other")


# ---------------------------------------------------------------------------
# Health & Info
# ---------------------------------------------------------------------------

@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "DataScout",
        "version": "0.2.0",
        "description": "Automated Dataset Search Agent on CROO Network",
        "ai_backend": "DeepSeek V4 Flash (ds2api proxy)",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Query Parsing
# ---------------------------------------------------------------------------

@app.post("/api/v1/parse")
async def parse_query(input_data: dict[str, Any]) -> dict[str, Any]:
    """Parse user query into structured parameters.

    Accepts three input types:
    - {"query": "..."} — Natural language query (parsed via DeepSeek V4 Flash)
    - {"topic": "...", "region": "..."} — Pre-structured params (used directly)
    - {"url": "https://..."} — Dataset URL for verification
    """
    try:
        parser = get_parser()
        parsed: ParsedQuery = await parser.parse(input_data)
        return {
            "status": "success",
            "parsed": parsed.model_dump(),
            "model_used": parsed.model_used,
            "parsing_time_ms": parsed.parsing_time_ms,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Parse error: %s", e)
        raise HTTPException(status_code=500, detail=f"Parse failed: {e}")


# ---------------------------------------------------------------------------
# CAP Protocol — Negotiation
# ---------------------------------------------------------------------------

@app.post("/api/v1/cap/negotiate")
async def cap_negotiate(input_data: dict[str, Any]) -> dict[str, Any]:
    """Estimate price for a dataset search query (CAP negotiation phase)."""
    try:
        parser = get_parser()
        parsed = await parser.parse(input_data)
        negotiation = estimate_price(parsed)
        return {
            "status": "success",
            "parsed_query": parsed.model_dump(),
            "negotiation": negotiation.model_dump(),
        }
    except Exception as e:
        logger.error("Negotiation error: %s", e)
        raise HTTPException(status_code=500, detail=f"Negotiation failed: {e}")


# ---------------------------------------------------------------------------
# CAP Protocol — Orders
# ---------------------------------------------------------------------------

@app.post("/api/v1/cap/orders")
async def create_order(order_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new CAP order (simulated)."""
    order = CapOrder(
        order_id=order_data.get("order_id", f"ord-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"),
        buyer_wallet=order_data.get("buyer_wallet", "0x0000"),
        agent_id="datascout-agent-001",
        capability="dataset_search",
        query_data=order_data.get("query_data", {}),
        status=CapOrderStatus.LOCKED,
        price_usdc=order_data.get("price_usdc", 0.05),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _orders[order.order_id] = order
    logger.info("Order created: %s — %.4f USDC", order.order_id, order.price_usdc)
    return {"status": "success", "order": order.model_dump()}


@app.get("/api/v1/cap/orders/{order_id}")
async def get_order(order_id: str) -> dict[str, Any]:
    """Get CAP order status."""
    order = _orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return {"status": "success", "order": order.model_dump()}


# ---------------------------------------------------------------------------
# CAP Protocol — Deliver
# ---------------------------------------------------------------------------

@app.post("/api/v1/cap/orders/{order_id}/deliver")
async def deliver_order(order_id: str, delivery_data: dict[str, Any]) -> dict[str, Any]:
    """Submit delivery for an order (CAP deliver phase)."""
    order = _orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    from src.models.report import FinalReport

    parsed_query = _build_parsed_query(order.query_data)

    report = FinalReport(
        query=parsed_query,
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_sources_searched=delivery_data.get("sources_searched", 0),
        total_results_found=delivery_data.get("datasets_found", 0),
        deduped_results=delivery_data.get("datasets_found", 0),
        summary=delivery_data.get("summary", "Search completed"),
    )

    delivery = format_delivery(
        order_id=order_id,
        agent_id=order.agent_id,
        report=report,
        execution_time_ms=delivery_data.get("execution_time_ms", 0),
    )

    order.status = CapOrderStatus.DELIVERED
    logger.info("Delivery submitted for order %s", order_id)
    return {"status": "success", "delivery": delivery.model_dump()}


# ---------------------------------------------------------------------------
# CAP Protocol — Clear (Settlement)
# ---------------------------------------------------------------------------

@app.post("/api/v1/cap/orders/{order_id}/clear")
async def clear_order(order_id: str) -> dict[str, Any]:
    """Settle an order (CAP clear phase)."""
    order = _orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    settlement = process_clear(
        order_id=order_id,
        delivery_hash=generate_hash_proof({"order_id": order_id}),
        price_usdc=order.price_usdc or 0.0,
    )

    order.status = CapOrderStatus.COMPLETED
    logger.info("Order cleared: %s — payment=%.4f USDC", order_id, order.price_usdc)
    return {"status": "success", "settlement": settlement.model_dump()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
