"""data.gov (Socrata) dataset search adapter — US government open data."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain mapping: Socrata domain_category → DataScout domain
# ---------------------------------------------------------------------------

_SOCRATA_CATEGORY_TO_DOMAIN: dict[str, str] = {
    "finance": "finance",
    "economy": "finance",
    "business": "finance",
    "health": "health",
    "public health": "health",
    "environment": "climate",
    "climate": "climate",
    "energy": "climate",
    "education": "education",
    "science and research": "nlp",
    "public safety": "social",
    "law enforcement": "social",
    "housing": "finance",
    "transportation": "tabular",
    "agriculture": "climate",
}


class DataGovAdapter(BaseSearchAdapter):
    """Search datasets on data.gov using the Socrata Open Data API.

    Free, no API key required (optional app token for higher rate limits).
    """

    BASE_URL = "https://api.us.socrata.com/api/catalog/v1"
    SOURCE_NAME = "data_gov"
    DEFAULT_TIMEOUT = 30

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        search_terms = [parsed_query.topic] + parsed_query.keywords[:3]
        params: dict[str, Any] = {
            "q": " ".join(search_terms),
            "domains": "data.gov",
            "limit": min(limit, 100),
        }
        if offset > 0:
            params["offset"] = offset

        # Add category filter if domain maps to a Socrata category
        category = self._domain_to_category(parsed_query.domain)
        if category:
            params["categories"] = category

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("data.gov API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("data.gov request failed: %s", exc)
            return []

        results_raw = data.get("results", [])
        if not results_raw:
            logger.info("data.gov returned 0 results for query: %s", parsed_query.topic)
            return []

        results = [self._parse_result(r, parsed_query) for r in results_raw]
        logger.info("data.gov returned %d results", len(results))
        return results

    def _parse_result(self, raw: dict[str, Any], parsed_query: ParsedQuery) -> DatasetResult:
        res = raw.get("resource", {})
        meta = raw.get("metadata", {})
        classification = raw.get("classification", {})

        # Parse domain categories
        domain_cats = classification.get("domain_category", [])
        tags = [c.get("name", "") for c in domain_cats if c.get("name")]

        # Infer domain from categories
        domain = self._infer_domain(tags, parsed_query.domain)

        # Get download URL
        download_url = res.get("download_url")
        if not download_url:
            # Build URL from resource ID
            domain_list = raw.get("domain", [])
            if domain_list:
                domain_name = domain_list[0].get("name", "data.gov")
                download_url = f"https://{domain_name}/d/{res.get('id', '')}"

        return DatasetResult(
            id=f"datagov-{raw.get('id', '')}",
            title=res.get("name", ""),
            description=res.get("description", "")[:500],
            source=self.SOURCE_NAME,
            source_url=f"https://data.gov/dataset/{raw.get('name', raw.get('id', ''))}",
            download_url=download_url,
            rows=None,
            columns=None,
            file_size_mb=None,
            file_format=res.get("format", "unknown"),
            last_updated=meta.get("updated_at"),
            tags=tags,
            domain=domain,
            region="US",
        )

    def _infer_domain(self, tags: list[str], fallback: str) -> str:
        tags_lower = [t.lower() for t in tags]
        for tag in tags_lower:
            if tag in _SOCRATA_CATEGORY_TO_DOMAIN:
                return _SOCRATA_CATEGORY_TO_DOMAIN[tag]
        return fallback or "government"

    @staticmethod
    def _domain_to_category(domain: str) -> str | None:
        domain_map = {
            "finance": "finance",
            "health": "health",
            "climate": "environment",
            "education": "education",
        }
        return domain_map.get(domain.lower())
