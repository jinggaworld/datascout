"""Unit tests for the parallel search orchestrator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.engine.orchestrator import SearchOrchestrator, SearchStats, create_default_orchestrator
from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _q(topic: str = "climate", domain: str = "climate") -> ParsedQuery:
    return ParsedQuery(topic=topic, domain=domain)


def _result(source: str, title: str = "test") -> DatasetResult:
    return DatasetResult(id=f"{source}-1", title=title, source=source, source_url=f"https://{source}.org")


class MockAdapter(BaseSearchAdapter):
    """Test adapter that returns configurable results."""

    def __init__(self, results: list[DatasetResult] | None = None, delay: float = 0, fail: bool = False):
        self._results = results or []
        self._delay = delay
        self._fail = fail
        self.SOURCE_NAME = "mock"

    async def search(self, parsed_query, limit=20, offset=0):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._fail:
            raise RuntimeError("adapter failure")
        return self._results[:limit]

    async def health_check(self):
        return not self._fail


# ---------------------------------------------------------------------------
# SearchOrchestrator tests
# ---------------------------------------------------------------------------

class TestSearchOrchestrator:
    def setup_method(self):
        self.orch = SearchOrchestrator(timeout=10)

    def test_register_adapter(self):
        adapter = MockAdapter()
        self.orch.register_adapter("test", adapter)
        assert "test" in self.orch.adapter_names

    def test_unregister_adapter(self):
        adapter = MockAdapter()
        self.orch.register_adapter("test", adapter)
        self.orch.unregister_adapter("test")
        assert "test" not in self.orch.adapter_names

    def test_unregister_nonexistent(self):
        self.orch.unregister_adapter("nonexistent")  # should not raise

    @pytest.mark.asyncio
    async def test_search_all_empty(self):
        results, stats = await self.orch.search_all(_q())
        assert results == []
        assert stats.sources_searched == 0

    @pytest.mark.asyncio
    async def test_search_all_single_adapter(self):
        self.orch.register_adapter("mock1", MockAdapter(results=[_result("mock1", "A")]))
        results, stats = await self.orch.search_all(_q(), limit_per_source=5)
        assert len(results) == 1
        assert results[0].title == "A"
        assert stats.sources_succeeded == 1
        assert stats.total_results == 1

    @pytest.mark.asyncio
    async def test_search_all_multiple_adapters(self):
        self.orch.register_adapter("a", MockAdapter(results=[_result("a", "A")]))
        self.orch.register_adapter("b", MockAdapter(results=[_result("b", "B")]))
        self.orch.register_adapter("c", MockAdapter(results=[_result("c", "C")]))
        results, stats = await self.orch.search_all(_q())
        assert len(results) == 3
        assert stats.sources_succeeded == 3
        titles = {r.title for r in results}
        assert titles == {"A", "B", "C"}

    @pytest.mark.asyncio
    async def test_search_all_graceful_degradation(self):
        """If one adapter fails, others still return results."""
        self.orch.register_adapter("ok1", MockAdapter(results=[_result("ok1", "OK1")]))
        self.orch.register_adapter("fail", MockAdapter(fail=True))
        self.orch.register_adapter("ok2", MockAdapter(results=[_result("ok2", "OK2")]))
        results, stats = await self.orch.search_all(_q())
        assert len(results) == 2
        assert stats.sources_succeeded == 2
        assert stats.sources_failed == 1

    @pytest.mark.asyncio
    async def test_search_all_timeout(self):
        """Slow adapter gets timed out."""
        self.orch = SearchOrchestrator(timeout=0.1)
        self.orch.register_adapter("fast", MockAdapter(results=[_result("fast")]))
        self.orch.register_adapter("slow", MockAdapter(delay=5.0, results=[_result("slow")]))
        results, stats = await self.orch.search_all(_q())
        assert len(results) == 1
        assert stats.sources_timeout == 1
        assert stats.sources_succeeded == 1

    @pytest.mark.asyncio
    async def test_search_all_filter_sources(self):
        """Only search specified sources."""
        self.orch.register_adapter("a", MockAdapter(results=[_result("a")]))
        self.orch.register_adapter("b", MockAdapter(results=[_result("b")]))
        self.orch.register_adapter("c", MockAdapter(results=[_result("c")]))
        results, stats = await self.orch.search_all(_q(), sources=["a", "c"])
        assert len(results) == 2
        assert stats.sources_searched == 2

    @pytest.mark.asyncio
    async def test_search_stats(self):
        self.orch.register_adapter("ok", MockAdapter(results=[_result("ok")]))
        self.orch.register_adapter("fail", MockAdapter(fail=True))
        results, stats = await self.orch.search_all(_q())
        assert isinstance(stats, SearchStats)
        assert stats.sources_searched == 2
        assert stats.sources_succeeded == 1
        assert stats.sources_failed == 1
        assert stats.elapsed_ms >= 0
        assert "ok" in stats.per_source
        assert "fail" in stats.per_source

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        healthy = MockAdapter()
        unhealthy = MockAdapter(fail=True)
        self.orch.register_adapter("healthy", healthy)
        self.orch.register_adapter("unhealthy", unhealthy)
        results = await self.orch.health_check_all()
        assert results["healthy"] is True
        assert results["unhealthy"] is False

    @pytest.mark.asyncio
    async def test_search_all_timeout_stats(self):
        self.orch = SearchOrchestrator(timeout=0.1)
        self.orch.register_adapter("slow", MockAdapter(delay=5.0))
        _, stats = await self.orch.search_all(_q())
        assert stats.sources_timeout == 1
        assert stats.per_source["slow"]["status"] == "timeout"


# ---------------------------------------------------------------------------
# create_default_orchestrator tests
# ---------------------------------------------------------------------------

class TestCreateDefault:
    def test_creates_with_all_adapters(self):
        orch = create_default_orchestrator()
        assert len(orch.adapter_names) == 10
        expected = {"huggingface", "kaggle", "openml", "zenodo", "data_gov",
                     "worldbank", "fred", "noaa", "openaq", "arxiv"}
        assert set(orch.adapter_names) == expected

    def test_timeout_configured(self):
        orch = create_default_orchestrator(timeout=60)
        assert orch.timeout == 60
