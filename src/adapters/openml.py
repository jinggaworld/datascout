"""OpenML dataset search adapter — standardized ML datasets with quality metadata."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain mapping: OpenML task types → DataScout domain
# ---------------------------------------------------------------------------

_OPENML_TASK_TO_DOMAIN: dict[str, str] = {
    "classification": "nlp",
    "regression": "tabular",
    "clustering": "tabular",
    "text": "nlp",
    "image": "cv",
    "time-series": "time_series",
    "tabular": "tabular",
}


class OpenMLAdapter(BaseSearchAdapter):
    """Search datasets on OpenML — free, no API key required.

    OpenML provides standardized ML datasets with rich quality metadata.
    """

    BASE_URL = "https://www.openml.org/api/v1/json"
    SOURCE_NAME = "openml"
    DEFAULT_TIMEOUT = 30

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        search_term = parsed_query.keywords[0] if parsed_query.keywords else parsed_query.topic
        url = f"{self.BASE_URL}/data/list/data_name/{search_term}/limit/{limit}"

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenML API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("OpenML request failed: %s", exc)
            return []

        datasets = data.get("data", {}).get("dataset", [])
        if not datasets:
            return []

        # OpenML can return a single dict instead of a list
        if isinstance(datasets, dict):
            datasets = [datasets]

        results = [r for d in datasets if isinstance(d, dict) and (r := self._parse_dataset(d, parsed_query)) is not None]
        logger.info("OpenML returned %d results", len(results))
        return results

    def _parse_dataset(self, raw: dict[str, Any], parsed_query: ParsedQuery) -> DatasetResult | None:
        if not isinstance(raw, dict):
            return None
        did = raw.get("did", "")
        name = raw.get("name", "")
        description = raw.get("description", "")

        # Parse numeric fields safely
        try:
            rows = int(raw.get("NumberOfInstances", 0)) if raw.get("NumberOfInstances") else None
        except (ValueError, TypeError):
            rows = None
        try:
            columns = int(raw.get("NumberOfFeatures", 0)) if raw.get("NumberOfFeatures") else None
        except (ValueError, TypeError):
            columns = None

        # Tags from task type and format
        tags: list[str] = []
        task_type = raw.get("task_type", "")
        if task_type:
            tags.append(task_type.lower())
        file_format = raw.get("format", "ARFF")
        if file_format:
            tags.append(file_format.lower())

        # Infer domain from task type
        domain = self._infer_domain(task_type, parsed_query.domain)

        return DatasetResult(
            id=f"openml-{did}",
            title=name or str(did),
            description=description[:500] if description else "",
            source=self.SOURCE_NAME,
            source_url=f"https://www.openml.org/d/{did}",
            download_url=f"https://www.openml.org/api/v1/json/data/{did}",
            rows=rows,
            columns=columns,
            file_size_mb=None,
            file_format=file_format or "ARFF",
            tags=tags,
            domain=domain,
            region=None,
        )

    def _infer_domain(self, task_type: str, fallback: str) -> str:
        task_lower = task_type.lower()
        for keyword, domain in _OPENML_TASK_TO_DOMAIN.items():
            if keyword in task_lower:
                return domain
        return fallback or "ml"
