"""OpenAQ air quality adapter — global air quality measurement data."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)


class OpenAQAdapter(BaseSearchAdapter):
    """Search air quality locations on OpenAQ.

    Free, no API key required.
    """

    BASE_URL = "https://api.openaq.org/v2"
    SOURCE_NAME = "openaq"
    DEFAULT_TIMEOUT = 30

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        params: dict[str, Any] = {
            "limit": min(limit, 100),
            "order_by": "lastUpdated",
            "sort": "desc",
        }
        if offset > 0:
            params["page"] = (offset // limit) + 1

        # Filter by country if specified
        if parsed_query.region:
            params["country"] = parsed_query.region.upper()

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(f"{self.BASE_URL}/locations", params=params)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAQ API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("OpenAQ request failed: %s", exc)
            return []

        locations = data.get("results", [])
        if not locations:
            logger.info("OpenAQ returned 0 results")
            return []

        results = [self._parse_location(loc, parsed_query) for loc in locations]
        logger.info("OpenAQ returned %d results", len(results))
        return results

    def _parse_location(self, loc: dict[str, Any], parsed_query: ParsedQuery) -> DatasetResult:
        location_id = loc.get("id", "")
        name = loc.get("name", "")
        city = loc.get("city", "")
        country = loc.get("country", "")
        country_name = loc.get("countryName", "")

        # Get coordinates
        coordinates = loc.get("coordinates", {})
        latitude = coordinates.get("latitude")
        longitude = coordinates.get("longitude")

        # Get measurements info
        measurements = loc.get("measurements", [])
        tags = ["air quality", "pollution"]
        if city:
            tags.append(city.lower())
        if country_name:
            tags.append(country_name.lower())

        # Build description from available info
        description_parts = []
        if city:
            description_parts.append(f"City: {city}")
        if country_name:
            description_parts.append(f"Country: {country_name}")
        if measurements:
            sources = set()
            for m in measurements:
                param = m.get("parameter", {})
                if isinstance(param, dict):
                    sources.add(param.get("name", ""))
            if sources:
                description_parts.append(f"Pollutants: {', '.join(sorted(sources))}")

        return DatasetResult(
            id=f"openaq-{location_id}",
            title=name or f"Air Quality - {city}, {country_name}",
            description=" | ".join(description_parts) if description_parts else name,
            source=self.SOURCE_NAME,
            source_url=f"https://openaq.org/#/locations/{location_id}",
            download_url=None,
            rows=None,
            columns=None,
            file_size_mb=None,
            file_format=None,
            last_updated=loc.get("lastUpdated"),
            tags=tags,
            domain="climate",
            region=country or parsed_query.region,
        )
