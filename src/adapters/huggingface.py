"""HuggingFace Datasets Hub adapter — searches the largest open-source dataset repository."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain mapping: HuggingFace tag → DataScout domain
# ---------------------------------------------------------------------------

HF_TAG_TO_DOMAIN: dict[str, list[str]] = {
    "finance": ["finance", "stock", "market", "economic", "trading", "banking"],
    "health": ["medical", "healthcare", "clinical", "biomedical", "protein", "drug"],
    "climate": ["climate", "weather", "environment", "earth", "ocean", "air quality"],
    "nlp": ["nlp", "text", "language", "sentiment", "ner", "translation", "summarization"],
    "cv": ["image", "vision", "video", "object detection", "segmentation", "ocr"],
    "audio": ["audio", "speech", "sound", "music", "asr"],
    "tabular": ["tabular", "csv", "structured", "tabular data"],
    "time_series": ["time-series", "forecasting", "ts", "temporal"],
    "social": ["social media", "twitter", "reddit", "reviews", "survey"],
    "geospatial": ["geospatial", "gis", "map", "location", "satellite"],
    "legal": ["legal", "law", "court", "regulation"],
    "education": ["education", "student", "academic", "school"],
}

# Reverse index: HF keyword → DataScout domain
_HF_KEYWORD_TO_DOMAIN: dict[str, str] = {}
for _domain, _keywords in HF_TAG_TO_DOMAIN.items():
    for _kw in _keywords:
        _HF_KEYWORD_TO_DOMAIN[_kw] = _domain


class HuggingFaceAdapter(BaseSearchAdapter):
    """Search datasets on the HuggingFace Datasets Hub.

    Uses the public REST API (no auth required for read access).
    Rate limit: ~500 requests/hour unauthenticated.
    """

    BASE_URL = "https://huggingface.co/api/datasets"
    SOURCE_NAME = "huggingface"
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
        """Search HuggingFace for datasets matching the parsed query."""
        params = self._build_params(parsed_query, limit, offset)

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                raw_datasets: list[dict[str, Any]] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("HuggingFace API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("HuggingFace request failed: %s", exc)
            return []

        if not raw_datasets:
            logger.info("HuggingFace returned 0 results for query: %s", parsed_query.topic)
            return []

        all_results = [self._parse_dataset(d, parsed_query) for d in raw_datasets]

        # Apply offset slicing (HF has no native offset param)
        sliced = all_results[offset: offset + limit] if offset > 0 else all_results[:limit]
        logger.info("HuggingFace returned %d results (raw=%d)", len(sliced), len(all_results))
        return sliced

    async def health_check(self) -> bool:
        """Verify HuggingFace API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.BASE_URL, params={"limit": 1})
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.warning("HuggingFace health check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_params(
        self,
        parsed_query: ParsedQuery,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """Build query parameters for the HuggingFace API.

        Note: We intentionally omit the ``filter`` parameter because
        HuggingFace's filter values are inconsistent and often kill
        results. Domain matching is handled via tag inference instead.
        """
        # Combine topic + keywords into a search string
        search_terms = [parsed_query.topic] + parsed_query.keywords
        params: dict[str, Any] = {
            "search": " ".join(search_terms),
            "limit": limit,
            "sort": "lastModified",
            "direction": -1,
        }

        # Pagination: HuggingFace has no native offset param,
        # so we fetch more items and let the caller slice.
        if offset > 0:
            params["limit"] = offset + limit

        return params

    def _parse_dataset(self, raw: dict[str, Any], parsed_query: ParsedQuery) -> DatasetResult:
        """Convert a raw HuggingFace dataset dict to a DatasetResult."""
        dataset_id: str = raw.get("id", "")
        tags: list[str] = raw.get("tags", [])
        stats = raw.get("stats") or {}

        # Extract row/column counts from stats (coerce to int)
        raw_rows = stats.get("examples") or stats.get("rows")
        try:
            rows = int(raw_rows) if raw_rows is not None else None
        except (ValueError, TypeError):
            rows = None
        columns = stats.get("features")
        if isinstance(columns, list):
            columns = len(columns)

        # Determine domain from tags
        domain = self._infer_domain(tags, parsed_query.domain)

        # Build download URL (parquet by default on HF)
        download_url = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/data"

        return DatasetResult(
            id=f"hf-{dataset_id}",
            title=dataset_id,
            description=raw.get("description", "") or dataset_id,
            source=self.SOURCE_NAME,
            source_url=f"https://huggingface.co/datasets/{dataset_id}",
            download_url=download_url,
            rows=rows,
            columns=columns if isinstance(columns, int) else None,
            file_size_mb=None,
            file_format="parquet",
            last_updated=raw.get("lastModified") or raw.get("last_modified"),
            tags=tags,
            domain=domain,
            region=None,
        )

    def _infer_domain(self, hf_tags: list[str], fallback_domain: str) -> str:
        """Infer DataScout domain from HuggingFace tags."""
        tags_lower = [t.lower() for t in hf_tags]
        for hf_keyword, ds_domain in _HF_KEYWORD_TO_DOMAIN.items():
            if hf_keyword in tags_lower:
                return ds_domain
        return fallback_domain or "other"

    @staticmethod
    def _domain_to_hf_tag(domain: str) -> Optional[str]:
        """Map a DataScout domain to a HuggingFace filter tag.

        TODO: Enable when HuggingFace stabilises their filter API.
        Currently unused because the ``filter`` param kills search results.
        """
        domain_map = {
            "finance": "finance",
            "health": "medical",
            "climate": "climate",
            "nlp": "nlp",
            "cv": "image",
            "audio": "audio",
            "social": "social-media",
            "education": "education",
        }
        return domain_map.get(domain.lower())
