"""arXiv dataset search adapter — academic papers with dataset links."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# arXiv Atom namespace
_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArXivAdapter(BaseSearchAdapter):
    """Search papers on arXiv — free, no API key required.

    Note: arXiv rate limit is ~1 request per 3 seconds.
    """

    BASE_URL = "http://export.arxiv.org/api"
    SOURCE_NAME = "arxiv"
    DEFAULT_TIMEOUT = 30

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        search_terms = [parsed_query.topic] + parsed_query.keywords[:3]
        search_query = " AND ".join(search_terms)

        params: dict[str, Any] = {
            "search_query": f"all:{search_query}",
            "start": offset,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.get(f"{self.BASE_URL}/query", params=params)
                resp.raise_for_status()
                xml_text = resp.text
        except httpx.HTTPStatusError as exc:
            logger.error("arXiv API error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.error("arXiv request failed: %s", exc)
            return []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("arXiv XML parse error: %s", exc)
            return []

        entries = root.findall("atom:entry", _NS)
        if not entries:
            logger.info("arXiv returned 0 results for query: %s", parsed_query.topic)
            return []

        results = [self._parse_entry(e) for e in entries]
        logger.info("arXiv returned %d results", len(results))
        return results

    def _parse_entry(self, entry: Any) -> DatasetResult:
        title_el = entry.find("atom:title", _NS)
        summary_el = entry.find("atom:summary", _NS)
        id_el = entry.find("atom:id", _NS)

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
        arxiv_url = id_el.text.strip() if id_el is not None and id_el.text else ""

        # Extract arXiv ID from URL
        arxiv_id = arxiv_url.split("/")[-1] if arxiv_url else ""

        # Find PDF link
        links = entry.findall("atom:link", _NS)
        pdf_link = None
        for link in links:
            if link.get("title") == "pdf":
                pdf_link = link.get("href")
                break

        # Get categories
        categories = []
        for cat in entry.findall("atom:category", _NS):
            term = cat.get("term", "")
            if term:
                categories.append(term)

        return DatasetResult(
            id=f"arxiv-{arxiv_id}",
            title=title,
            description=summary[:500],
            source=self.SOURCE_NAME,
            source_url=arxiv_url,
            download_url=pdf_link,
            rows=None,
            columns=None,
            file_size_mb=None,
            file_format="pdf",
            tags=categories,
            domain="academic",
            region=None,
        )
