"""NOAA Climate Data adapter — global weather and climate datasets."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.adapters.base import BaseSearchAdapter
from src.config import get_settings
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)


class NOAAAdapter(BaseSearchAdapter):
    """Search datasets on NOAA Climate Data Online.

    Requires a free API key from ncdc.noaa.gov.
    """

    BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    SOURCE_NAME = "noaa"
    DEFAULT_TIMEOUT = 30

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        settings = get_settings()
        api_key = settings.noaa_api_key

        if not api_key:
            logger.warning("NOAA_API_KEY not configured — skipping NOAA search")
            return []

        headers = {"token": api_key}

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/datasets",
                    params={"limit": min(limit, 25)},
                    headers=headers,
                )
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("NOAA API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("NOAA request failed: %s", exc)
            return []

        datasets = data.get("results", [])
        if not datasets:
            logger.info("NOAA returned 0 results")
            return []

        results = [self._parse_dataset(d, parsed_query) for d in datasets]
        logger.info("NOAA returned %d results", len(results))
        return results

    def _parse_dataset(self, dataset: dict[str, Any], parsed_query: ParsedQuery) -> DatasetResult:
        dataset_id = dataset.get("id", "")
        name = dataset.get("name", "")
        description = dataset.get("description", "")

        tags = ["climate", "weather"]
        if dataset_id:
            tags.append(dataset_id.lower())

        return DatasetResult(
            id=f"noaa-{dataset_id}",
            title=name or dataset_id,
            description=description[:500] if description else name,
            source=self.SOURCE_NAME,
            source_url=f"https://www.ncdc.noaa.gov/cdo-web/datasets/{dataset_id}",
            download_url=None,
            rows=None,
            columns=None,
            file_size_mb=None,
            file_format="csv",
            tags=tags,
            domain="climate",
            region="global",
        )
