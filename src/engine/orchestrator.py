"""Parallel search orchestrator — coordinates concurrent searches across all adapters."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)


@dataclass
class SearchStats:
    """Aggregated search statistics."""

    total_results: int = 0
    sources_searched: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    sources_timeout: int = 0
    elapsed_ms: int = 0
    per_source: dict[str, dict[str, int | str]] = field(default_factory=dict)


class SearchOrchestrator:
    """Execute parallel searches across multiple dataset adapters.

    Each adapter runs concurrently via asyncio.gather. If one adapter
    fails or times out, the others continue unaffected.
    """

    DEFAULT_TIMEOUT = 30  # seconds per adapter

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.adapters: dict[str, BaseSearchAdapter] = {}
        self.timeout = timeout

    def register_adapter(self, name: str, adapter: BaseSearchAdapter) -> None:
        """Register a search adapter."""
        self.adapters[name] = adapter
        logger.debug("Registered adapter: %s (%s)", name, adapter.__class__.__name__)

    def unregister_adapter(self, name: str) -> None:
        """Remove a search adapter."""
        self.adapters.pop(name, None)

    @property
    def adapter_names(self) -> list[str]:
        return list(self.adapters.keys())

    async def search_all(
        self,
        parsed_query: ParsedQuery,
        limit_per_source: int = 20,
        sources: list[str] | None = None,
    ) -> tuple[list[DatasetResult], SearchStats]:
        """Execute parallel search across all (or selected) registered adapters.

        Args:
            parsed_query: Structured query from the AI parser.
            limit_per_source: Max results per adapter.
            sources: Optional list of adapter names to search. If None, searches all.

        Returns:
            Tuple of (flattened results list, search statistics).
        """
        start = time.monotonic()
        stats = SearchStats()

        # Determine which adapters to query
        target_adapters = {
            name: adapter
            for name, adapter in self.adapters.items()
            if sources is None or name in sources
        }
        stats.sources_searched = len(target_adapters)

        if not target_adapters:
            logger.warning("No adapters registered or matched for search")
            return [], stats

        # Build parallel tasks
        tasks = {
            name: self._safe_search(name, adapter, parsed_query, limit_per_source)
            for name, adapter in target_adapters.items()
        }

        # Execute all searches concurrently
        results_map = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True,
        )

        # Aggregate results
        all_results: list[DatasetResult] = []
        for name, result in zip(tasks.keys(), results_map):
            if isinstance(result, list):
                all_results.extend(result)
                count = len(result)
                stats.sources_succeeded += 1
                stats.per_source[name] = {"status": "ok", "count": count}
                logger.info("Adapter %s returned %d results", name, count)
            elif isinstance(result, asyncio.TimeoutError):
                stats.sources_timeout += 1
                stats.per_source[name] = {"status": "timeout", "count": 0}
                logger.warning("Adapter %s timed out after %ds", name, self.timeout)
            elif isinstance(result, Exception):
                stats.sources_failed += 1
                stats.per_source[name] = {"status": "error", "count": 0, "error": str(result)}
                logger.error("Adapter %s failed: %s", name, result)

        elapsed = int((time.monotonic() - start) * 1000)
        stats.total_results = len(all_results)
        stats.elapsed_ms = elapsed

        logger.info(
            "Search complete: %d results from %d/%d sources in %dms",
            stats.total_results,
            stats.sources_succeeded,
            stats.sources_searched,
            stats.elapsed_ms,
        )

        return all_results, stats

    async def _safe_search(
        self,
        name: str,
        adapter: BaseSearchAdapter,
        query: ParsedQuery,
        limit: int,
    ) -> list[DatasetResult]:
        """Run a single adapter search with timeout and error handling."""
        return await asyncio.wait_for(
            adapter.search(query, limit=limit),
            timeout=self.timeout,
        )

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all registered adapters."""
        results: dict[str, bool] = {}
        for name, adapter in self.adapters.items():
            try:
                results[name] = await asyncio.wait_for(
                    adapter.health_check(),
                    timeout=10,
                )
            except Exception:
                results[name] = False
        return results


def create_default_orchestrator(timeout: int = 30) -> SearchOrchestrator:
    """Create an orchestrator with all available adapters pre-registered.

    Adapters that require missing API keys will still be registered
    but will return empty results gracefully.
    """
    from src.adapters.arxiv import ArXivAdapter
    from src.adapters.data_gov import DataGovAdapter
    from src.adapters.fred import FredAdapter
    from src.adapters.huggingface import HuggingFaceAdapter
    from src.adapters.kaggle import KaggleAdapter
    from src.adapters.noaa import NOAAAdapter
    from src.adapters.openaq import OpenAQAdapter
    from src.adapters.openml import OpenMLAdapter
    from src.adapters.worldbank import WorldBankAdapter
    from src.adapters.zenodo import ZenodoAdapter

    orch = SearchOrchestrator(timeout=timeout)

    adapters: list[tuple[str, BaseSearchAdapter]] = [
        ("huggingface", HuggingFaceAdapter()),
        ("kaggle", KaggleAdapter()),
        ("openml", OpenMLAdapter()),
        ("zenodo", ZenodoAdapter()),
        ("data_gov", DataGovAdapter()),
        ("worldbank", WorldBankAdapter()),
        ("fred", FredAdapter()),
        ("noaa", NOAAAdapter()),
        ("openaq", OpenAQAdapter()),
        ("arxiv", ArXivAdapter()),
    ]

    for name, adapter in adapters:
        orch.register_adapter(name, adapter)

    return orch
