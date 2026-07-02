"""Unit tests for OpenML, Zenodo, data.gov, World Bank, NOAA, OpenAQ, arXiv adapters."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.openml import OpenMLAdapter
from src.adapters.zenodo import ZenodoAdapter
from src.adapters.data_gov import DataGovAdapter
from src.adapters.worldbank import WorldBankAdapter
from src.adapters.noaa import NOAAAdapter
from src.adapters.openaq import OpenAQAdapter
from src.adapters.arxiv import ArXivAdapter
from src.adapters.base import BaseSearchAdapter
from src.models.query import ParsedQuery


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _q(topic: str = "climate", domain: str = "climate", **kw) -> ParsedQuery:
    return ParsedQuery(topic=topic, domain=domain, **kw)


# ---------------------------------------------------------------------------
# OpenML
# ---------------------------------------------------------------------------

class TestOpenMLAdapter:
    def setup_method(self):
        self.adapter = OpenMLAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "openml"

    def test_is_base(self):
        assert isinstance(self.adapter, BaseSearchAdapter)

    @pytest.mark.asyncio
    async def test_search_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"dataset": [
            {"did": 31, "name": "iris", "NumberOfInstances": 150, "NumberOfFeatures": 4, "format": "ARFF", "task_type": "Classification"}
        ]}}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.openml.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q(topic="iris"), limit=5)
        assert len(results) == 1
        assert results[0].id == "openml-31"
        assert results[0].rows == 150

    @pytest.mark.asyncio
    async def test_search_empty(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"dataset": []}}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.openml.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q())
        assert results == []

    @pytest.mark.asyncio
    async def test_search_single_dict(self):
        """OpenML sometimes returns a single dict instead of list."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"dataset": {"did": 1, "name": "test"}}}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.openml.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q())
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Zenodo
# ---------------------------------------------------------------------------

class TestZenodoAdapter:
    def setup_method(self):
        self.adapter = ZenodoAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "zenodo"

    @pytest.mark.asyncio
    async def test_search_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"hits": {"hits": [
            {"id": 12345, "doi": "10.5281/zenodo.12345", "created": "2024-01-01",
             "metadata": {"title": "Climate Data", "description": "Test", "license": "cc-by",
                          "keywords": [{"tag": "climate"}, {"tag": "temperature"}]},
             "files": [{"size": 5000000, "links": {"self": "https://zenodo.org/api/files/test"}}]}
        ]}}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.zenodo.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q(), limit=5)
        assert len(results) == 1
        assert results[0].id == "zenodo-12345"
        assert results[0].tags == ["climate", "temperature"]

    @pytest.mark.asyncio
    async def test_search_empty(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"hits": {"hits": []}}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.zenodo.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q())
        assert results == []


# ---------------------------------------------------------------------------
# data.gov
# ---------------------------------------------------------------------------

class TestDataGovAdapter:
    def setup_method(self):
        self.adapter = DataGovAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "data_gov"

    @pytest.mark.asyncio
    async def test_search_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [
            {"id": "abc-123", "resource": {"name": "US Housing", "description": "Test", "format": "CSV"},
             "metadata": {"updated_at": "2024-01-01"},
             "classification": {"domain_category": [{"name": "Housing"}]},
             "domain": [{"name": "data.gov"}]}
        ]}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.data_gov.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q(topic="housing", domain="finance"), limit=5)
        assert len(results) == 1
        assert results[0].id == "datagov-abc-123"
        assert results[0].region == "US"

    @pytest.mark.asyncio
    async def test_search_empty(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.data_gov.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q())
        assert results == []


# ---------------------------------------------------------------------------
# World Bank
# ---------------------------------------------------------------------------

class TestWorldBankAdapter:
    def setup_method(self):
        self.adapter = WorldBankAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "worldbank"

    @pytest.mark.asyncio
    async def test_search_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # World Bank returns [metadata, data]
        mock_resp.json.return_value = [
            {"page": 1, "pages": 1, "total": 1},
            [{"id": "NY.GDP.MKTP.CD", "name": "GDP", "note": "Gross Domestic Product",
              "country": {"value": "Indonesia"}}]
        ]
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.worldbank.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q(topic="gdp", domain="finance"), limit=5)
        assert len(results) == 1
        assert results[0].id == "wb-NY.GDP.MKTP.CD"

    @pytest.mark.asyncio
    async def test_search_empty(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"page": 1}, []]
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.worldbank.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q())
        assert results == []


# ---------------------------------------------------------------------------
# NOAA
# ---------------------------------------------------------------------------

class TestNOAAAdapter:
    def setup_method(self):
        self.adapter = NOAAAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "noaa"

    @pytest.mark.asyncio
    async def test_search_no_key(self):
        with patch("src.adapters.noaa.get_settings") as ms:
            ms.return_value = MagicMock(noaa_api_key="")
            results = await self.adapter.search(_q())
            assert results == []

    @pytest.mark.asyncio
    async def test_search_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [
            {"id": "GHCND", "name": "Daily Summaries", "description": "Daily weather data"}
        ]}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.noaa.get_settings") as ms:
            ms.return_value = MagicMock(noaa_api_key="test_key")
            with patch("src.adapters.noaa.httpx.AsyncClient") as MC:
                inst = AsyncMock()
                inst.get = AsyncMock(return_value=mock_resp)
                inst.__aenter__ = AsyncMock(return_value=inst)
                inst.__aexit__ = AsyncMock(return_value=False)
                MC.return_value = inst
                results = await self.adapter.search(_q(), limit=5)
        assert len(results) == 1
        assert results[0].id == "noaa-GHCND"


# ---------------------------------------------------------------------------
# OpenAQ
# ---------------------------------------------------------------------------

class TestOpenAQAdapter:
    def setup_method(self):
        self.adapter = OpenAQAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "openaq"

    @pytest.mark.asyncio
    async def test_search_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [
            {"id": 1, "name": "Station Jakarta", "city": "Jakarta", "country": "ID",
             "countryName": "Indonesia", "coordinates": {"latitude": -6.2, "longitude": 106.8},
             "measurements": [{"parameter": {"name": "pm25"}}],
             "lastUpdated": "2024-01-01"}
        ]}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.openaq.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q(), limit=5)
        assert len(results) == 1
        assert results[0].id == "openaq-1"
        assert "jakarta" in results[0].tags


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------

class TestArXivAdapter:
    def setup_method(self):
        self.adapter = ArXivAdapter()

    def test_source_name(self):
        assert self.adapter.SOURCE_NAME == "arxiv"

    @pytest.mark.asyncio
    async def test_search_success(self):
        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2401.12345</id>
            <title>Climate Dataset Analysis</title>
            <summary>A paper about climate data.</summary>
            <category term="cs.CL"/>
            <link title="pdf" href="https://arxiv.org/pdf/2401.12345"/>
          </entry>
        </feed>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = xml_response
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.arxiv.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q(), limit=5)
        assert len(results) == 1
        assert results[0].id == "arxiv-2401.12345"
        assert results[0].title == "Climate Dataset Analysis"
        assert results[0].download_url == "https://arxiv.org/pdf/2401.12345"

    @pytest.mark.asyncio
    async def test_search_empty(self):
        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom"></feed>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = xml_response
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.arxiv.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q())
        assert results == []

    @pytest.mark.asyncio
    async def test_search_xml_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "not xml"
        mock_resp.raise_for_status = MagicMock()
        with patch("src.adapters.arxiv.httpx.AsyncClient") as MC:
            inst = AsyncMock()
            inst.get = AsyncMock(return_value=mock_resp)
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            results = await self.adapter.search(_q())
        assert results == []


# ---------------------------------------------------------------------------
# Error handling across all adapters
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_openml_http_error(self):
        adapter = OpenMLAdapter()
        with patch("src.adapters.openml.httpx.AsyncClient") as MC:
            import httpx
            inst = AsyncMock()
            resp = MagicMock()
            resp.status_code = 500
            inst.get = AsyncMock(side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=resp))
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            assert await adapter.search(_q()) == []

    @pytest.mark.asyncio
    async def test_zenodo_request_error(self):
        adapter = ZenodoAdapter()
        with patch("src.adapters.zenodo.httpx.AsyncClient") as MC:
            import httpx
            inst = AsyncMock()
            inst.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            assert await adapter.search(_q()) == []

    @pytest.mark.asyncio
    async def test_datagov_http_error(self):
        adapter = DataGovAdapter()
        with patch("src.adapters.data_gov.httpx.AsyncClient") as MC:
            import httpx
            inst = AsyncMock()
            resp = MagicMock()
            resp.status_code = 429
            inst.get = AsyncMock(side_effect=httpx.HTTPStatusError("rate", request=MagicMock(), response=resp))
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            assert await adapter.search(_q()) == []

    @pytest.mark.asyncio
    async def test_noaa_http_error(self):
        adapter = NOAAAdapter()
        with patch("src.adapters.noaa.get_settings") as ms:
            ms.return_value = MagicMock(noaa_api_key="key")
            with patch("src.adapters.noaa.httpx.AsyncClient") as MC:
                import httpx
                inst = AsyncMock()
                resp = MagicMock()
                resp.status_code = 403
                inst.get = AsyncMock(side_effect=httpx.HTTPStatusError("forbidden", request=MagicMock(), response=resp))
                inst.__aenter__ = AsyncMock(return_value=inst)
                inst.__aexit__ = AsyncMock(return_value=False)
                MC.return_value = inst
                assert await adapter.search(_q()) == []

    @pytest.mark.asyncio
    async def test_openaq_request_error(self):
        adapter = OpenAQAdapter()
        with patch("src.adapters.openaq.httpx.AsyncClient") as MC:
            import httpx
            inst = AsyncMock()
            inst.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            assert await adapter.search(_q()) == []

    @pytest.mark.asyncio
    async def test_arxiv_http_error(self):
        adapter = ArXivAdapter()
        with patch("src.adapters.arxiv.httpx.AsyncClient") as MC:
            import httpx
            inst = AsyncMock()
            resp = MagicMock()
            resp.status_code = 503
            inst.get = AsyncMock(side_effect=httpx.HTTPStatusError("unavailable", request=MagicMock(), response=resp))
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            assert await adapter.search(_q()) == []

    @pytest.mark.asyncio
    async def test_worldbank_request_error(self):
        adapter = WorldBankAdapter()
        with patch("src.adapters.worldbank.httpx.AsyncClient") as MC:
            import httpx
            inst = AsyncMock()
            inst.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__ = AsyncMock(return_value=False)
            MC.return_value = inst
            assert await adapter.search(_q()) == []
