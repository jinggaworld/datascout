"""DataScout API — Automated Dataset Search Agent on CROO Network.

Production mode: connects to CROO Agent Store via CAP Protocol.
- On startup: registers agent, connects WebSocket, listens for orders
- Direct API: /api/v1/search still works for demo/testing
- CROO status: /api/v1/cap/status shows connection health
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.cap.clear import process_clear
from src.cap.deliver import format_delivery, generate_hash_proof
from src.cap.handler import OrderHandler
from src.cap.negotiation import estimate_price
from src.cap.registration import deregister_agent, register_agent
from src.config import get_settings
from src.engine.dedup import DeduplicationEngine
from src.engine.license import LicenseExtractor
from src.engine.orchestrator import create_default_orchestrator
from src.engine.ranking import RankingEngine
from src.engine.score import ReadinessCalculator
from src.groq.parser import QueryParser
from src.models.cap import CapOrder, CapOrderStatus
from src.models.query import ParsedQuery
from src.report.generator import ReportGenerator, generate_markdown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------
_parser: QueryParser | None = None
_orchestrator = None
_license_extractor = LicenseExtractor()
_ranking_engine = RankingEngine()
_dedup_engine = DeduplicationEngine()
_score_calculator = ReadinessCalculator()
_report_generator = ReportGenerator()

# CAP singletons
from src.cap.client import CapClient

_cap_client = CapClient()
_order_handler = OrderHandler()


def get_parser() -> QueryParser:
    global _parser
    if _parser is None:
        _parser = QueryParser()
    return _parser


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_default_orchestrator()
    return _orchestrator


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
# CAP order handler — called by WebSocket listener
# ---------------------------------------------------------------------------

async def _on_cap_order(message: dict[str, Any]) -> None:
    """Handle incoming CAP order events from CROO WebSocket."""
    msg_type = message.get("type", "")

    if msg_type == "order.locked":
        order_data = message.get("payload", message)
        order = _order_handler.create_order(order_data)
        logger.info("CAP order locked: %s — processing...", order.order_id)

        # Process in background so WebSocket listener isn't blocked
        asyncio.create_task(
            _order_handler.process_order(order, cap_client=_cap_client)
        )

    elif msg_type == "order.cancelled":
        order_id = message.get("order_id") or message.get("payload", {}).get("order_id")
        if order_id:
            order = _order_handler.get_order(order_id)
            if order:
                order.status = CapOrderStatus.FAILED
                logger.info("CAP order cancelled: %s", order_id)

    elif msg_type == "ping":
        await _cap_client.send({"type": "pong"})

    else:
        logger.debug("Unhandled CROO message type: %s", msg_type)


# Register the handler
_cap_client.on_message(_on_cap_order)


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: register agent + connect WebSocket. Shutdown: graceful disconnect."""
    from src.config import get_settings
    settings = get_settings()

    # Register with CROO Agent Store (non-blocking, failure OK)
    if settings.cap_auto_connect and settings.cap_agent_id:
        logger.info("Registering agent with CROO Agent Store...")
        try:
            reg_result = await register_agent()
            logger.info("Registration result: %s", reg_result.get("status"))
        except Exception as e:
            logger.warning("CROO registration failed (non-critical): %s", e)

        # Connect WebSocket listener
        logger.info("Connecting to CROO WebSocket...")
        try:
            await _cap_client.start_listener()
        except Exception as e:
            logger.warning("CROO WebSocket connect failed: %s", e)

        if _cap_client.is_connected:
            logger.info("Listening for CAP orders on CROO network")
        else:
            logger.warning("CROO WebSocket not connected — direct API mode only")
    else:
        logger.info("CAP auto-connect disabled — running in direct API mode")

    yield

    # Shutdown
    logger.info("Shutting down DataScout...")
    try:
        await _cap_client.disconnect()
    except Exception:
        pass
    try:
        await deregister_agent()
    except Exception:
        pass
    logger.info("DataScout stopped")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DataScout API",
    description="Automated Dataset Search, Scoring & Reporting Agent on CROO Network",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Search Pipeline (direct API — works with or without CROO)
# ---------------------------------------------------------------------------

@app.post("/api/v1/search")
async def search_datasets(input_data: dict[str, Any]) -> dict[str, Any]:
    """Full search pipeline: parse -> search -> dedup -> rank -> license -> score -> report."""
    start = time.monotonic()

    try:
        parser = get_parser()
        parsed: ParsedQuery = await parser.parse(input_data)

        orch = get_orchestrator()
        raw_results, stats = await orch.search_all(parsed, limit_per_source=20)

        deduped = _dedup_engine.deduplicate(raw_results)
        ranked = _ranking_engine.rank(parsed, deduped)
        licensed = _license_extractor.extract_batch(ranked)
        scored = _score_calculator.calculate_batch(licensed)

        report = _report_generator.generate(
            query=parsed,
            datasets=scored,
            stats={
                "sources_searched": stats.sources_searched,
                "elapsed_ms": stats.elapsed_ms,
            },
        )

        elapsed = int((time.monotonic() - start) * 1000)

        return {
            "status": "success",
            "elapsed_ms": elapsed,
            "report": report.model_dump(),
            "markdown": generate_markdown(report),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Search pipeline error: %s", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


# ---------------------------------------------------------------------------
# Health & Info
# ---------------------------------------------------------------------------

@app.get("/")
async def root() -> dict[str, Any]:
    settings = get_settings()
    return {
        "name": "DataScout",
        "version": "0.3.0",
        "description": "Automated Dataset Search Agent on CROO Network",
        "status": "running",
        "croo_connected": _cap_client.is_connected,
        "ai_backend": settings.ai_backend,
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "croo_connected": _cap_client.is_connected,
    }


# ---------------------------------------------------------------------------
# CAP Protocol Status
# ---------------------------------------------------------------------------

@app.get("/api/v1/cap/status")
async def cap_status() -> dict[str, Any]:
    """CROO connection status, agent info, and order stats."""
    return {
        "connection": _cap_client.get_status(),
        "orders": _order_handler.get_stats(),
        "version": "0.3.0",
    }


# ---------------------------------------------------------------------------
# Query Parsing
# ---------------------------------------------------------------------------

@app.post("/api/v1/parse")
async def parse_query(input_data: dict[str, Any]) -> dict[str, Any]:
    """Parse user query into structured parameters."""
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
    """Create a new CAP order and process it through the pipeline."""
    order = _order_handler.create_order(order_data)

    # Process in background
    asyncio.create_task(
        _order_handler.process_order(order, cap_client=_cap_client)
    )

    return {"status": "success", "order": order.model_dump()}


@app.get("/api/v1/cap/orders/{order_id}")
async def get_order(order_id: str) -> dict[str, Any]:
    """Get CAP order status."""
    order = _order_handler.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return {"status": "success", "order": order.model_dump()}


@app.get("/api/v1/cap/orders")
async def list_orders() -> dict[str, Any]:
    """List all CAP orders."""
    orders = _order_handler.get_all_orders()
    return {
        "status": "success",
        "orders": {k: v.model_dump() for k, v in orders.items()},
        "stats": _order_handler.get_stats(),
    }


# ---------------------------------------------------------------------------
# CAP Protocol — Deliver
# ---------------------------------------------------------------------------

@app.post("/api/v1/cap/orders/{order_id}/deliver")
async def deliver_order(order_id: str, delivery_data: dict[str, Any]) -> dict[str, Any]:
    """Submit delivery for an order (CAP deliver phase)."""
    order = _order_handler.get_order(order_id)
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
    order = _order_handler.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    settlement = await process_clear(
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
