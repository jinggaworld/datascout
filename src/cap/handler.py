"""Order handler: receive CAP order -> run pipeline -> deliver -> clear."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from src.cap.clear import process_clear
from src.cap.deliver import format_delivery
from src.cap.negotiation import estimate_price
from src.engine.dedup import DeduplicationEngine
from src.engine.license import LicenseExtractor
from src.engine.orchestrator import create_default_orchestrator
from src.engine.ranking import RankingEngine
from src.engine.score import ReadinessCalculator
from src.groq.parser import QueryParser
from src.models.cap import CapOrder, CapOrderStatus
from src.models.query import ParsedQuery
from src.report.generator import ReportGenerator

logger = logging.getLogger(__name__)


class OrderHandler:
    """Processes incoming CAP orders through the full DataScout pipeline."""

    def __init__(self) -> None:
        self._parser: QueryParser | None = None
        self._orchestrator = None
        self._dedup = DeduplicationEngine()
        self._ranking = RankingEngine()
        self._license = LicenseExtractor()
        self._scorer = ReadinessCalculator()
        self._reporter = ReportGenerator()
        self._orders: dict[str, CapOrder] = {}

    def _get_parser(self) -> QueryParser:
        if self._parser is None:
            self._parser = QueryParser()
        return self._parser

    def _get_orchestrator(self):
        if self._orchestrator is None:
            self._orchestrator = create_default_orchestrator()
        return self._orchestrator

    def get_order(self, order_id: str) -> CapOrder | None:
        return self._orders.get(order_id)

    def get_all_orders(self) -> dict[str, CapOrder]:
        return dict(self._orders)

    def get_stats(self) -> dict[str, Any]:
        statuses = {}
        for o in self._orders.values():
            statuses[o.status.value] = statuses.get(o.status.value, 0) + 1
        return {
            "total_orders": len(self._orders),
            "by_status": statuses,
        }

    def _build_query(self, data: dict[str, Any]) -> ParsedQuery:
        """Construct ParsedQuery from order query_data."""
        if "query" in data:
            return ParsedQuery(topic="pending", domain="other")
        if "topic" in data:
            from src.models.query import LicenseFilter

            lic = data.get("license", "any")
            if isinstance(lic, str):
                lic = LicenseFilter(lic)
            return ParsedQuery(
                topic=data["topic"],
                keywords=data.get("keywords", []),
                region=data.get("region"),
                domain=data.get("domain", "other"),
                license=lic,
                min_rows=data.get("min_rows"),
            )
        raise ValueError(
            f"Invalid query_data: must contain 'query' or 'topic', got: {list(data.keys())}"
        )

    async def process_order(
        self,
        order: CapOrder,
        cap_client: Any = None,
    ) -> dict[str, Any]:
        """Full order lifecycle: lock -> search pipeline -> deliver -> clear.

        Returns the final settlement result.
        """
        order.status = CapOrderStatus.DELIVERING
        start = time.monotonic()
        logger.info("Processing order %s: %s", order.order_id, order.query_data)

        try:
            # 1. Parse the query
            parser = self._get_parser()
            parsed = await parser.parse(order.query_data)
            logger.info(
                "Order %s: parsed topic=%s, domain=%s",
                order.order_id,
                parsed.topic,
                parsed.domain,
            )

            # 2. Run the full search pipeline
            orch = self._get_orchestrator()
            raw_results, stats = await orch.search_all(parsed, limit_per_source=20)

            # 3. Deduplicate
            deduped = self._dedup.deduplicate(raw_results)

            # 4. Rank by relevance
            ranked = self._ranking.rank(parsed, deduped)

            # 5. Extract licenses
            licensed = self._license.extract_batch(ranked)

            # 6. Calculate readiness scores
            scored = self._scorer.calculate_batch(licensed)

            # 7. Generate report
            report = self._reporter.generate(
                query=parsed,
                datasets=scored,
                stats={
                    "sources_searched": stats.sources_searched,
                    "elapsed_ms": stats.elapsed_ms,
                },
            )

            elapsed_ms = int((time.monotonic() - start) * 1000)

            # 8. Format delivery
            delivery = format_delivery(
                order_id=order.order_id,
                agent_id=order.agent_id,
                report=report,
                execution_time_ms=elapsed_ms,
            )

            order.status = CapOrderStatus.DELIVERED

            # 9. Submit delivery to CROO via REST API
            if cap_client and cap_client.is_connected:
                from src.report.generator import generate_markdown

                result = await cap_client.deliver_order(
                    order_id=order.order_id,
                    content={
                        "report": report.model_dump(),
                        "markdown": generate_markdown(report),
                        "datasets_found": delivery.datasets_found,
                        "sources_searched": delivery.sources_searched,
                        "execution_time_ms": elapsed_ms,
                        "hash_proof": delivery.hash_proof,
                    },
                    deliverable_type="json",
                )
                logger.info(
                    "Delivery submitted to CROO for order %s: %s",
                    order.order_id,
                    result.get("status", "unknown"),
                )

            # 10. Clear / settle
            settlement = await process_clear(
                order_id=order.order_id,
                delivery_hash=delivery.hash_proof,
                price_usdc=order.price_usdc or 0.0,
            )

            order.status = CapOrderStatus.COMPLETED

            logger.info(
                "Order %s completed: %d datasets, %.4f USDC, %dms",
                order.order_id,
                delivery.datasets_found,
                order.price_usdc or 0.0,
                elapsed_ms,
            )

            return {
                "status": "completed",
                "order_id": order.order_id,
                "delivery": delivery.model_dump(),
                "settlement": settlement.model_dump(),
                "elapsed_ms": elapsed_ms,
                "datasets_found": delivery.datasets_found,
                "sources_searched": delivery.sources_searched,
            }

        except Exception as e:
            order.status = CapOrderStatus.FAILED
            logger.error("Order %s failed: %s", order.order_id, e)
            return {
                "status": "failed",
                "order_id": order.order_id,
                "error": str(e),
            }

    def create_order(
        self,
        order_data: dict[str, Any],
    ) -> CapOrder:
        """Create and store a new order (from CROO or direct API)."""
        from src.config import get_settings

        settings = get_settings()
        order_id = order_data.get(
            "order_id",
            f"ord-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        )

        # Extract query data from CROO event payload
        query_data = order_data.get("query_data", {})
        if not query_data:
            # Try common CROO payload structures
            query_data = order_data.get("input", order_data.get("request", {}))
        if not query_data:
            query_data = order_data

        # Estimate price if not provided
        price = order_data.get("price_usdc")
        if price is None:
            try:
                parsed = self._build_query(query_data)
                negotiation = estimate_price(parsed)
                price = negotiation.total_price_usdc
            except Exception:
                price = 0.03  # fallback

        order = CapOrder(
            order_id=order_id,
            buyer_wallet=order_data.get(
                "buyer_wallet",
                order_data.get("requester_wallet", "0x0000"),
            ),
            agent_id=settings.cap_agent_id or "datascout-agent-001",
            capability="dataset_search",
            query_data=query_data,
            status=CapOrderStatus.LOCKED,
            price_usdc=price,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._orders[order.order_id] = order
        logger.info(
            "Order created: %s — %.4f USDC",
            order.order_id,
            order.price_usdc,
        )
        return order
