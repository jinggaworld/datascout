"""Unit tests for Kaggle and FRED dataset search adapters."""

from __future__ import annotations

import csv
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.kaggle import KaggleAdapter, _KAGGLE_TAG_TO_DOMAIN
from src.adapters.fred import FredAdapter, _FRED_KEYWORD_TO_DOMAIN
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_KAGGLE_CSV = """\
ref,name,subtitle,totalBytes,fileType,tags,lastUpdated
tunguz/real-or-not-real-nlp-with-disaster-tweets,Real or Not? NLP with Disaster Tweets,NLP classification of real vs fake disaster tweets,2400000,zip,"nlp,text,classification",2020-06-04
budhwani/who-s-twitter-data,Who's Twitter Data,Twitter sentiment data,1200000,csv,"twitter,social media,sentiment",2021-03-15
"""

SAMPLE_KAGGLE_ROW = {
    "ref": "stanford/imdb",
    "name": "IMDB Reviews",
    "subtitle": "Movie review sentiment dataset",
    "totalBytes": "50000000",
    "fileType": "csv",
    "tags": "nlp,text,sentiment,movie",
    "lastUpdated": "2023-01-15",
}

SAMPLE_FRED_SERIES = {
    "id": "GDP",
    "title": "Gross Domestic Product",
    "notes": "GDP measures the value of goods and services produced.",
    "frequency": "Quarterly",
    "units": "Billions of Dollars",
    "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
    "observation_start": "1947-04-01",
    "observation_end": "2024-01-01",
    "last_updated": "2024-03-28T08:01:04-05:00",
}

SAMPLE_FRED_SERIES_MINIMAL = {
    "id": "UNRATE",
    "title": "Unemployment Rate",
}


def _make_query(topic: str = "climate", domain: str = "climate", **kwargs) -> ParsedQuery:
    return ParsedQuery(topic=topic, domain=domain, **kwargs)


# ---------------------------------------------------------------------------
# KaggleAdapter tests
# ---------------------------------------------------------------------------


class TestKaggleAdapter:
    def setup_method(self):
        self.adapter = KaggleAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "kaggle"

    def test_build_command_basic(self):
        query = _make_query(topic="housing prices", domain="finance")
        cmd = self.adapter._build_command(query, limit=10)
        assert cmd[0] == "kaggle"
        assert cmd[1] == "datasets"
        assert cmd[2] == "list"
        assert "-s" in cmd
        assert "housing prices" in cmd[cmd.index("-s") + 1]
        assert "--csv" in cmd

    def test_build_command_with_keywords(self):
        query = _make_query(topic="sentiment", domain="nlp", keywords=["text", "reviews"])
        cmd = self.adapter._build_command(query, limit=5)
        idx = cmd.index("-s")
        search_str = cmd[idx + 1]
        assert "sentiment" in search_str
        assert "text" in search_str
        assert "reviews" in search_str

    def test_build_command_with_format(self):
        query = _make_query(topic="test", domain="other", format=["csv"])
        cmd = self.adapter._build_command(query, limit=5)
        assert "--file-type" in cmd
        assert "csv" in cmd

    def test_parse_row_full(self):
        result = self.adapter._parse_row(SAMPLE_KAGGLE_ROW, _make_query())
        assert result.id == "kaggle-stanford/imdb"
        assert result.title == "IMDB Reviews"
        assert result.source == "kaggle"
        assert result.file_size_mb == 50.0
        assert result.file_format == "csv"
        assert result.source_url == "https://www.kaggle.com/datasets/stanford/imdb"
        assert "nlp" in result.tags
        assert result.domain == "nlp"

    def test_parse_row_missing_fields(self):
        minimal_row = {"ref": "test/dataset"}
        result = self.adapter._parse_row(minimal_row, _make_query(domain="other"))
        assert result.id == "kaggle-test/dataset"
        assert result.file_size_mb is None
        assert result.tags == []

    def test_parse_csv_output(self):
        results = self.adapter._parse_csv_output(SAMPLE_KAGGLE_CSV, _make_query())
        assert len(results) == 2
        assert results[0].id == "kaggle-tunguz/real-or-not-real-nlp-with-disaster-tweets"
        assert results[0].domain == "nlp"
        assert results[1].id == "kaggle-budhwani/who-s-twitter-data"
        assert results[1].domain == "social"

    def test_infer_domain_from_tags(self):
        assert self.adapter._infer_domain(["nlp", "sentiment"], "other") == "nlp"
        assert self.adapter._infer_domain(["finance", "stock"], "other") == "finance"
        assert self.adapter._infer_domain(["medical"], "other") == "health"
        assert self.adapter._infer_domain(["weather"], "other") == "climate"
        assert self.adapter._infer_domain(["unknown"], "other") == "other"

    def test_infer_domain_fallback(self):
        assert self.adapter._infer_domain([], "finance") == "finance"
        assert self.adapter._infer_domain([], "") == "other"

    @pytest.mark.asyncio
    async def test_search_cli_not_found(self):
        query = _make_query(topic="test", domain="other")
        with patch("src.adapters.kaggle.shutil.which", return_value=None):
            results = await self.adapter.search(query)
            assert results == []

    @pytest.mark.asyncio
    async def test_search_success(self):
        query = _make_query(topic="sentiment", domain="nlp")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = SAMPLE_KAGGLE_CSV
        mock_result.stderr = ""

        with patch("src.adapters.kaggle.shutil.which", return_value="/usr/bin/kaggle"):
            with patch("src.adapters.kaggle.subprocess.run", return_value=mock_result):
                results = await self.adapter.search(query, limit=5)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_empty_output(self):
        query = _make_query(topic="nonexistent", domain="other")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("src.adapters.kaggle.shutil.which", return_value="/usr/bin/kaggle"):
            with patch("src.adapters.kaggle.subprocess.run", return_value=mock_result):
                results = await self.adapter.search(query)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_cli_error(self):
        query = _make_query(topic="test", domain="other")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: API error"

        with patch("src.adapters.kaggle.shutil.which", return_value="/usr/bin/kaggle"):
            with patch("src.adapters.kaggle.subprocess.run", return_value=mock_result):
                results = await self.adapter.search(query)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_timeout(self):
        import subprocess as sp

        query = _make_query(topic="test", domain="other")
        with patch("src.adapters.kaggle.shutil.which", return_value="/usr/bin/kaggle"):
            with patch(
                "src.adapters.kaggle.subprocess.run",
                side_effect=sp.TimeoutExpired(cmd="kaggle", timeout=30),
            ):
                results = await self.adapter.search(query)

        assert results == []


# ---------------------------------------------------------------------------
# FredAdapter tests
# ---------------------------------------------------------------------------


class TestFredAdapter:
    def setup_method(self):
        self.adapter = FredAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "fred"

    def test_build_params_basic(self):
        query = _make_query(topic="gdp", domain="finance")
        params = self.adapter._build_params(query, api_key="test_key", limit=10, offset=0)
        assert params["search_text"] == "gdp"
        assert params["api_key"] == "test_key"
        assert params["file_type"] == "json"
        assert params["limit"] == 10
        assert params["offset"] == 0
        assert params["order_by"] == "search_rank"

    def test_build_params_with_keywords(self):
        query = _make_query(topic="unemployment", domain="finance", keywords=["rate", "labor"])
        params = self.adapter._build_params(query, api_key="key", limit=5, offset=10)
        assert params["search_text"] == "unemployment rate labor"
        assert params["limit"] == 5
        assert params["offset"] == 10

    def test_build_params_with_domain_tag(self):
        query = _make_query(topic="health", domain="health")
        params = self.adapter._build_params(query, api_key="key", limit=10, offset=0)
        assert params.get("tag_names") == "health"

    def test_parse_series_full(self):
        result = self.adapter._parse_series(SAMPLE_FRED_SERIES, _make_query())
        assert result.id == "fred-GDP"
        assert result.title == "Gross Domestic Product"
        assert result.source == "fred"
        assert result.source_url == "https://fred.stlouisfed.org/series/GDP"
        assert result.download_url is not None
        assert "GDP" in result.download_url
        assert result.file_format == "csv"
        assert result.region == "US"
        assert "quarterly" in result.tags
        assert result.domain == "finance"

    def test_parse_series_minimal(self):
        result = self.adapter._parse_series(SAMPLE_FRED_SERIES_MINIMAL, _make_query())
        assert result.id == "fred-UNRATE"
        assert result.title == "Unemployment Rate"
        assert result.download_url is not None
        assert result.domain == "finance"

    def test_infer_domain(self):
        assert self.adapter._infer_domain("GDP", "Gross Domestic Product", "other") == "finance"
        assert self.adapter._infer_domain("UNRATE", "Unemployment Rate", "other") == "finance"
        assert self.adapter._infer_domain("ENV", "Environment Data", "other") == "climate"
        assert self.adapter._infer_domain("EDU", "Education Stats", "other") == "education"
        assert self.adapter._infer_domain("UNKNOWN", "Something else", "other") == "other"

    def test_infer_domain_fallback(self):
        assert self.adapter._infer_domain("X", "X", "climate") == "climate"
        assert self.adapter._infer_domain("X", "X", "") == "finance"

    def test_domain_to_fred_tag(self):
        assert FredAdapter._domain_to_fred_tag("finance") == "gdp"
        assert FredAdapter._domain_to_fred_tag("health") == "health"
        assert FredAdapter._domain_to_fred_tag("nonexistent") is None

    @pytest.mark.asyncio
    async def test_search_no_api_key(self):
        query = _make_query(topic="gdp", domain="finance")
        with patch("src.adapters.fred.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(fred_api_key="")
            results = await self.adapter.search(query)
            assert results == []

    @pytest.mark.asyncio
    async def test_search_success(self):
        query = _make_query(topic="gdp", domain="finance")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "seriess": [SAMPLE_FRED_SERIES, SAMPLE_FRED_SERIES_MINIMAL]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("src.adapters.fred.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(fred_api_key="test_key")
            with patch("src.adapters.fred.httpx.AsyncClient") as MockClient:
                instance = AsyncMock()
                instance.get = AsyncMock(return_value=mock_response)
                instance.__aenter__ = AsyncMock(return_value=instance)
                instance.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = instance

                results = await self.adapter.search(query, limit=5)

        assert len(results) == 2
        assert results[0].id == "fred-GDP"
        assert results[1].id == "fred-UNRATE"

    @pytest.mark.asyncio
    async def test_search_empty(self):
        query = _make_query(topic="nonexistent", domain="other")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"seriess": []}
        mock_response.raise_for_status = MagicMock()

        with patch("src.adapters.fred.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(fred_api_key="test_key")
            with patch("src.adapters.fred.httpx.AsyncClient") as MockClient:
                instance = AsyncMock()
                instance.get = AsyncMock(return_value=mock_response)
                instance.__aenter__ = AsyncMock(return_value=instance)
                instance.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = instance

                results = await self.adapter.search(query)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        query = _make_query(topic="gdp", domain="finance")

        with patch("src.adapters.fred.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(fred_api_key="test_key")
            with patch("src.adapters.fred.httpx.AsyncClient") as MockClient:
                import httpx

                instance = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.status_code = 403
                instance.get = AsyncMock(
                    side_effect=httpx.HTTPStatusError(
                        "forbidden", request=MagicMock(), response=mock_resp
                    )
                )
                instance.__aenter__ = AsyncMock(return_value=instance)
                instance.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = instance

                results = await self.adapter.search(query)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_request_error(self):
        query = _make_query(topic="gdp", domain="finance")

        with patch("src.adapters.fred.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(fred_api_key="test_key")
            with patch("src.adapters.fred.httpx.AsyncClient") as MockClient:
                import httpx

                instance = AsyncMock()
                instance.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
                instance.__aenter__ = AsyncMock(return_value=instance)
                instance.__aexit__ = AsyncMock(return_value=False)
                MockClient.return_value = instance

                results = await self.adapter.search(query)

        assert results == []


# ---------------------------------------------------------------------------
# Domain mapping tests
# ---------------------------------------------------------------------------


class TestDomainMappings:
    def test_kaggle_tags_cover_common_domains(self):
        assert "finance" in _KAGGLE_TAG_TO_DOMAIN
        assert "nlp" in _KAGGLE_TAG_TO_DOMAIN
        assert "climate" in _KAGGLE_TAG_TO_DOMAIN
        assert "health" in _KAGGLE_TAG_TO_DOMAIN

    def test_fred_keywords_cover_finance(self):
        assert "gdp" in _FRED_KEYWORD_TO_DOMAIN
        assert "unemployment" in _FRED_KEYWORD_TO_DOMAIN
        assert "inflation" in _FRED_KEYWORD_TO_DOMAIN
