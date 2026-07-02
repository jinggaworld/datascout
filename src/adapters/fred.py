"""FRED (Federal Reserve Economic Data) adapter — searches economic datasets from the St. Louis Fed."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from src.adapters.base import BaseSearchAdapter
from src.config import get_settings
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain mapping: FRED tags/keywords → DataScout domain
# ---------------------------------------------------------------------------

_FRED_KEYWORD_TO_DOMAIN: dict[str, str] = {
    "gdp": "finance",
    "inflation": "finance",
    "unemployment": "finance",
    "interest rate": "finance",
    "consumer price": "finance",
    "stock": "finance",
    "trade": "finance",
    "federal reserve": "finance",
    "housing": "finance",
    "mortgage": "finance",
    "employment": "finance",
    "labor": "finance",
    "cpi": "finance",
    "ppi": "finance",
    "industrial production": "finance",
    "retail sales": "finance",
    "personal income": "finance",
    "population": "social",
    "education": "education",
    "health": "health",
    "energy": "climate",
    "environment": "climate",
    "weather": "climate",
}


class FredAdapter(BaseSearchAdapter):
    """Search economic datasets on FRED (Federal Reserve Economic Data).

    Uses the FRED public REST API. Requires a free API key from
    https://fred.stlouisfed.org/docs/api/api_key.html
    """

    BASE_URL = "https://api.stlouisfed.org/fred/series/search"
    SOURCE_NAME = "fred"
    DEFAULT_TIMEOUT = 30  # seconds

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        """Search FRED for economic data series matching the parsed query."""
        settings = get_settings()
        api_key = settings.fred_api_key

        if not api_key:
            logger.warning("FRED_API_KEY not configured — skipping FRED search")
            return []

        params = self._build_params(parsed_query, api_key, limit, offset)

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("FRED API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("FRED request failed: %s", exc)
            return []

        series_list: list[dict[str, Any]] = data.get("seriess", [])
        if not series_list:
            logger.info("FRED returned 0 results for query: %s", parsed_query.topic)
            return []

        results = [self._parse_series(s, parsed_query) for s in series_list]
        logger.info("FRED returned %d results", len(results))
        return results

    async def health_check(self) -> bool:
        """Verify FRED API is reachable (does not validate API key)."""
        settings = get_settings()
        if not settings.fred_api_key:
            return False

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    self.BASE_URL,
                    params={
                        "search_text": "test",
                        "api_key": settings.fred_api_key,
                        "file_type": "json",
                        "limit": 1,
                    },
                )
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.warning("FRED health check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_params(
        self,
        parsed_query: ParsedQuery,
        api_key: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """Build query parameters for the FRED API."""
        # Combine topic + keywords into search text
        search_terms = [parsed_query.topic] + parsed_query.keywords
        search_text = " ".join(search_terms)

        params: dict[str, Any] = {
            "search_text": search_text,
            "api_key": api_key,
            "file_type": "json",
            "limit": limit,
            "offset": offset,
            "order_by": "search_rank",
            "sort_order": "desc",
        }

        # Add tag filter if domain maps to a FRED tag
        tag = self._domain_to_fred_tag(parsed_query.domain)
        if tag:
            params["tag_names"] = tag

        return params

    def _parse_series(self, series: dict[str, Any], parsed_query: ParsedQuery) -> DatasetResult:
        """Convert a FRED series object to a DatasetResult."""
        series_id: str = series.get("id", "")
        title: str = series.get("title", "")
        notes: str = series.get("notes", "")
        frequency: str = series.get("frequency", "")
        units: str = series.get("units", "")
        seasonal_adjustment: str = series.get("seasonal_adjustment", "")
        observation_start: str = series.get("observation_start", "")
        observation_end: str = series.get("observation_end", "")
        last_updated: str = series.get("last_updated", "")

        # Build description from available metadata
        description_parts = [notes] if notes else []
        if frequency:
            description_parts.append(f"Frequency: {frequency}")
        if units:
            description_parts.append(f"Units: {units}")
        if seasonal_adjustment:
            description_parts.append(f"Seasonal adjustment: {seasonal_adjustment}")
        description = " | ".join(description_parts) if description_parts else title

        # Build tags from metadata
        tags: list[str] = []
        if frequency:
            tags.append(frequency.lower())
        if units:
            tags.append(units.lower())
        if seasonal_adjustment:
            tags.append(seasonal_adjustment.lower())

        # Infer domain from series ID and title
        domain = self._infer_domain(series_id, title, parsed_query.domain)

        download_url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

        return DatasetResult(
            id=f"fred-{series_id}",
            title=title,
            description=description,
            source=self.SOURCE_NAME,
            source_url=f"https://fred.stlouisfed.org/series/{series_id}",
            download_url=download_url,
            rows=None,
            columns=None,
            file_size_mb=None,
            file_format="csv",
            last_updated=last_updated or None,
            tags=tags,
            domain=domain,
            region="US",
        )

    def _infer_domain(self, series_id: str, title: str, fallback_domain: str) -> str:
        """Infer DataScout domain from FRED series ID and title."""
        combined = f"{series_id.lower()} {title.lower()}"
        for keyword, domain in _FRED_KEYWORD_TO_DOMAIN.items():
            if keyword in combined:
                return domain
        return fallback_domain or "finance"

    @staticmethod
    def _domain_to_fred_tag(domain: str) -> Optional[str]:
        """Map a DataScout domain to a FRED tag name."""
        tag_map = {
            "finance": "gdp",
            "health": "health",
            "climate": "environment",
            "education": "education",
        }
        return tag_map.get(domain.lower())
