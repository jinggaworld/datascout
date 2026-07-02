"""Zenodo dataset search adapter — open science research datasets."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain mapping: Zenodo keywords → DataScout domain
# ---------------------------------------------------------------------------

_ZENODO_KEYWORD_TO_DOMAIN: dict[str, str] = {
    "climate": "climate",
    "weather": "climate",
    "environment": "climate",
    "ocean": "climate",
    "temperature": "climate",
    "gdp": "finance",
    "economic": "finance",
    "finance": "finance",
    "medical": "health",
    "health": "health",
    "clinical": "health",
    "protein": "health",
    "nlp": "nlp",
    "text": "nlp",
    "sentiment": "nlp",
    "image": "cv",
    "vision": "cv",
    "audio": "audio",
    "speech": "audio",
    "education": "education",
    "student": "education",
}


class ZenodoAdapter(BaseSearchAdapter):
    """Search datasets on Zenodo — open science platform for research data.

    Uses the public Zenodo REST API. No auth required for read access.
    Rate limit: ~100 requests/minute.
    """

    BASE_URL = "https://zenodo.org/api/records"
    SOURCE_NAME = "zenodo"
    DEFAULT_TIMEOUT = 30

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        # Combine topic + keywords
        search_terms = [parsed_query.topic] + parsed_query.keywords[:3]
        params: dict[str, Any] = {
            "q": " ".join(search_terms),
            "size": min(limit, 100),
            "page": max(1, (offset // limit) + 1),
            "type": "dataset",
        }

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Zenodo API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("Zenodo request failed: %s", exc)
            return []

        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            logger.info("Zenodo returned 0 results for query: %s", parsed_query.topic)
            return []

        results = [self._parse_hit(h, parsed_query) for h in hits]
        logger.info("Zenodo returned %d results", len(results))
        return results

    def _parse_hit(self, hit: dict[str, Any], parsed_query: ParsedQuery) -> DatasetResult:
        metadata = hit.get("metadata", {})
        files = hit.get("files", [])

        # Get download URL from first file
        download_url: str | None = None
        file_size_mb: float | None = None
        if files:
            first_file = files[0]
            links = first_file.get("links", {})
            download_url = links.get("self")
            size_bytes = first_file.get("size", 0)
            if size_bytes:
                file_size_mb = size_bytes / 1_000_000

        # Parse license
        license_info = metadata.get("license", "unknown")

        # Parse keywords/tags
        raw_keywords = metadata.get("keywords", [])
        tags: list[str] = []
        for kw in raw_keywords:
            if isinstance(kw, dict):
                tags.append(kw.get("tag", ""))
            elif isinstance(kw, str):
                tags.append(kw)

        # Get DOI
        doi = hit.get("doi", "")

        # Infer domain from keywords
        domain = self._infer_domain(tags, parsed_query.domain)

        record_id = hit.get("id", "")

        return DatasetResult(
            id=f"zenodo-{record_id}",
            title=metadata.get("title", ""),
            description=metadata.get("description", "")[:500],
            source=self.SOURCE_NAME,
            source_url=f"https://zenodo.org/record/{record_id}",
            download_url=download_url,
            rows=None,
            columns=None,
            file_size_mb=file_size_mb,
            file_format=None,
            last_updated=hit.get("created"),
            tags=tags,
            domain=domain,
            region=None,
        )

    def _infer_domain(self, tags: list[str], fallback: str) -> str:
        tags_lower = [t.lower() for t in tags]
        for keyword, domain in _ZENODO_KEYWORD_TO_DOMAIN.items():
            if keyword in " ".join(tags_lower):
                return domain
        return fallback or "research"
