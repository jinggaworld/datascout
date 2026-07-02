"""Unit tests for dataset search adapters — HuggingFace adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.base import BaseSearchAdapter
from src.adapters.huggingface import HuggingFaceAdapter, _HF_KEYWORD_TO_DOMAIN
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_HF_DATASET = {
    "id": "stanfordnlp/imdb",
    "tags": ["nlp", "sentiment", "movie-reviews", "text-classification"],
    "lastModified": "2024-01-15T10:30:00Z",
    "stats": {"rows": 50000, "features": 2},
    "description": "IMDB movie reviews for sentiment analysis",
}

SAMPLE_HF_DATASET_NO_STATS = {
    "id": "openai/openai-humaneval",
    "tags": ["code", "evaluation"],
    "lastModified": "2024-06-01T00:00:00Z",
}

SAMPLE_HF_DATASET_MINIMAL = {
    "id": "mystery/dataset",
}


def _make_query(topic: str = "sentiment", domain: str = "nlp", **kwargs) -> ParsedQuery:
    return ParsedQuery(topic=topic, domain=domain, **kwargs)


# ---------------------------------------------------------------------------
# BaseSearchAdapter tests
# ---------------------------------------------------------------------------


class TestBaseSearchAdapter:
    def test_is_abstract(self):
        """Cannot instantiate BaseSearchAdapter directly."""
        with pytest.raises(TypeError):
            BaseSearchAdapter()  # type: ignore[abstract]

    def test_repr(self):
        """Repr shows source name."""

        class Dummy(BaseSearchAdapter):
            SOURCE_NAME = "dummy"
            BASE_URL = "https://example.com"

            async def search(self, parsed_query, limit=20, offset=0):
                return []

        adapter = Dummy()
        assert "dummy" in repr(adapter)

    @pytest.mark.asyncio
    async def test_health_check_default(self):
        """Default health check returns True."""

        class Dummy(BaseSearchAdapter):
            SOURCE_NAME = "dummy"
            BASE_URL = "https://example.com"

            async def search(self, parsed_query, limit=20, offset=0):
                return []

        adapter = Dummy()
        assert await adapter.health_check() is True


# ---------------------------------------------------------------------------
# HuggingFaceAdapter tests
# ---------------------------------------------------------------------------


class TestHuggingFaceAdapter:
    def setup_method(self):
        self.adapter = HuggingFaceAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "huggingface"

    def test_is_base_adapter(self):
        assert isinstance(self.adapter, BaseSearchAdapter)

    def test_build_params_basic(self):
        query = _make_query(topic="climate", domain="climate")
        params = self.adapter._build_params(query, limit=10, offset=0)
        assert params["search"] == "climate"
        assert params["limit"] == 10
        assert params["sort"] == "lastModified"
        assert params["direction"] == -1
        assert "filter" not in params  # filter intentionally omitted

    def test_build_params_with_keywords(self):
        query = _make_query(topic="sentiment", domain="nlp", keywords=["text", "reviews"])
        params = self.adapter._build_params(query, limit=5, offset=0)
        assert params["search"] == "sentiment text reviews"

    def test_build_params_with_offset(self):
        query = _make_query(topic="climate", domain="climate")
        params = self.adapter._build_params(query, limit=10, offset=20)
        assert params["limit"] == 30  # offset + limit

    def test_parse_dataset_full(self):
        result = self.adapter._parse_dataset(SAMPLE_HF_DATASET, _make_query())
        assert result.id == "hf-stanfordnlp/imdb"
        assert result.title == "stanfordnlp/imdb"
        assert result.source == "huggingface"
        assert result.source_url == "https://huggingface.co/datasets/stanfordnlp/imdb"
        assert result.rows == 50000
        assert result.columns == 2
        assert result.last_updated == "2024-01-15T10:30:00Z"
        assert "nlp" in result.tags

    def test_parse_dataset_no_stats(self):
        result = self.adapter._parse_dataset(SAMPLE_HF_DATASET_NO_STATS, _make_query())
        assert result.id == "hf-openai/openai-humaneval"
        assert result.rows is None
        assert result.columns is None

    def test_parse_dataset_minimal(self):
        result = self.adapter._parse_dataset(SAMPLE_HF_DATASET_MINIMAL, _make_query(domain="other"))
        assert result.id == "hf-mystery/dataset"
        assert result.domain == "other"

    def test_infer_domain_from_tags(self):
        assert self.adapter._infer_domain(["nlp", "sentiment"], "other") == "nlp"
        assert self.adapter._infer_domain(["image", "segmentation"], "other") == "cv"
        assert self.adapter._infer_domain(["finance", "stock"], "other") == "finance"
        assert self.adapter._infer_domain(["medical", "clinical"], "other") == "health"
        assert self.adapter._infer_domain(["audio", "speech"], "other") == "audio"
        assert self.adapter._infer_domain(["unknown-tag"], "other") == "other"

    def test_infer_domain_fallback(self):
        assert self.adapter._infer_domain([], "climate") == "climate"
        assert self.adapter._infer_domain([], "") == "other"

    def test_domain_to_hf_tag(self):
        assert HuggingFaceAdapter._domain_to_hf_tag("nlp") == "nlp"
        assert HuggingFaceAdapter._domain_to_hf_tag("cv") == "image"
        assert HuggingFaceAdapter._domain_to_hf_tag("nonexistent") is None

    @pytest.mark.asyncio
    async def test_search_success(self):
        query = _make_query(topic="sentiment", domain="nlp")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [SAMPLE_HF_DATASET]
        mock_response.raise_for_status = MagicMock()

        with patch("src.adapters.huggingface.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = await self.adapter.search(query, limit=5)

        assert len(results) == 1
        assert results[0].id == "hf-stanfordnlp/imdb"

    @pytest.mark.asyncio
    async def test_search_empty(self):
        query = _make_query(topic="nonexistent", domain="other")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch("src.adapters.huggingface.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = await self.adapter.search(query, limit=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        """HTTP errors should be caught and return empty list."""
        query = _make_query(topic="test", domain="other")

        with patch("src.adapters.huggingface.httpx.AsyncClient") as MockClient:
            import httpx

            instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 429
            http_error = httpx.HTTPStatusError(
                "rate limited", request=MagicMock(), response=mock_response
            )
            instance.get = AsyncMock(side_effect=http_error)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = await self.adapter.search(query, limit=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_request_error(self):
        """Network errors should be caught and return empty list."""
        query = _make_query(topic="test", domain="other")

        with patch("src.adapters.huggingface.httpx.AsyncClient") as MockClient:
            import httpx

            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            results = await self.adapter.search(query, limit=5)

        assert results == []


# ---------------------------------------------------------------------------
# Domain mapping tests
# ---------------------------------------------------------------------------


class TestDomainMapping:
    def test_all_domains_have_keywords(self):
        """Every domain in the mapping has at least one keyword."""
        from src.adapters.huggingface import HF_TAG_TO_DOMAIN

        for domain, keywords in HF_TAG_TO_DOMAIN.items():
            assert len(keywords) > 0, f"Domain '{domain}' has no keywords"

    def test_reverse_index_is_consistent(self):
        """Reverse index covers all keywords from the forward mapping."""
        from src.adapters.huggingface import HF_TAG_TO_DOMAIN

        for domain, keywords in HF_TAG_TO_DOMAIN.items():
            for kw in keywords:
                assert kw in _HF_KEYWORD_TO_DOMAIN
                assert _HF_KEYWORD_TO_DOMAIN[kw] == domain
