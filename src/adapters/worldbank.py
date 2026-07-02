"""World Bank Open Data adapter — global economic and development indicators."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# Country code mapping: DataScout region → World Bank country code
_REGION_TO_WB: dict[str, str] = {
    "ID": "IDN",
    "US": "USA",
    "EU": "EUU",
    "GB": "GBR",
    "JP": "JPN",
    "CN": "CHN",
    "IN": "IND",
    "BR": "BRA",
    "DE": "DEU",
    "FR": "FRA",
}


class WorldBankAdapter(BaseSearchAdapter):
    """Search indicators on the World Bank Open Data API.

    Free, no API key required.
    """

    BASE_URL = "https://api.worldbank.org/v2"
    SOURCE_NAME = "worldbank"
    DEFAULT_TIMEOUT = 30

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        search_terms = [parsed_query.topic] + parsed_query.keywords[:2]
        params: dict[str, Any] = {
            "format": "json",
            "per_page": min(limit, 100),
            "q": " ".join(search_terms),
            "source": "2",  # World Development Indicators
        }
        if offset > 0:
            params["page"] = (offset // limit) + 1

        # Filter by region/country if specified
        if parsed_query.region:
            country = _REGION_TO_WB.get(parsed_query.region.upper(), parsed_query.region)
            params["country"] = country

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(f"{self.BASE_URL}/indicator", params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("World Bank API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("World Bank request failed: %s", exc)
            return []

        # World Bank returns [metadata, data]
        indicators = data[1] if isinstance(data, list) and len(data) > 1 else []
        if not isinstance(indicators, list):
            indicators = []
        if not indicators:
            logger.info("World Bank returned 0 results for query: %s", parsed_query.topic)
            return []

        results = [self._parse_indicator(i, parsed_query) for i in indicators]
        logger.info("World Bank returned %d results", len(results))
        return results

    def _parse_indicator(self, indicator: dict[str, Any], parsed_query: ParsedQuery) -> DatasetResult:
        indicator_id = indicator.get("id", "")
        name = indicator.get("name", "")
        note = indicator.get("note", "")

        # Extract country info
        country = indicator.get("country", {})
        country_name = country.get("value", "") if isinstance(country, dict) else ""

        tags = ["world bank", "economic"]
        if country_name:
            tags.append(country_name.lower())

        return DatasetResult(
            id=f"wb-{indicator_id}",
            title=name or indicator_id,
            description=note[:500] if note else name,
            source=self.SOURCE_NAME,
            source_url=f"https://data.worldbank.org/indicator/{indicator_id}",
            download_url=f"https://api.worldbank.org/v2/country/all/indicator/{indicator_id}?format=json&per_page=100",
            rows=None,
            columns=None,
            file_size_mb=None,
            file_format="json",
            last_updated=None,
            tags=tags,
            domain="finance",
            region=parsed_query.region or "global",
        )
