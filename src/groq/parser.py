import logging
import re
from datetime import datetime
from typing import Any

from src.groq.client import GroqClient
from src.groq.prompts import QUERY_PARSER_PROMPT
from src.models.query import IntentType, LicenseFilter, ParsedQuery, TimeRange

logger = logging.getLogger(__name__)

# Year range pattern for Indonesian/English queries
# Group 1+2: explicit range like "2019-2024"
# Group 3: "X tahun terakhir" (Indonesian)
# Group 4: "last X years" (English)
YEAR_RANGE_PATTERN = re.compile(
    r"(\d{4})\s*[-–]\s*(\d{4})|(\d+)\s*tahun\s*terakhir|(?:last|past)\s+(\d+)\s*years?",
    re.IGNORECASE,
)


class QueryParser:
    """Routes input to appropriate handler: natural language, structured, or URL."""

    def __init__(self) -> None:
        self.client = GroqClient()

    async def parse(self, input_data: dict[str, Any]) -> ParsedQuery:
        """Route input to the correct handler based on input type."""
        if "query" in input_data:
            return await self._parse_natural(input_data["query"])
        elif "topic" in input_data:
            return self._parse_structured(input_data)
        elif "url" in input_data:
            return self._parse_url(input_data["url"])
        else:
            raise ValueError(
                "Invalid input: must contain 'query' (natural language), "
                "'topic' (structured params), or 'url' (verification)"
            )

    async def _parse_natural(self, query: str) -> ParsedQuery:
        """Parse a natural language query via Groq API."""
        logger.info("Parsing natural language query: %s", query[:100])
        return await self.client.parse_query(query, QUERY_PARSER_PROMPT)

    def _parse_structured(self, data: dict[str, Any]) -> ParsedQuery:
        """Directly construct ParsedQuery from structured parameters."""
        logger.info("Using pre-structured params for topic: %s", data.get("topic"))
        time_range = None
        tr = data.get("time_range")
        if tr:
            if isinstance(tr, dict):
                time_range = TimeRange(**tr)
            elif isinstance(tr, TimeRange):
                time_range = tr

        lic = data.get("license", "any")
        if isinstance(lic, str):
            lic = LicenseFilter(lic)

        intent = data.get("intent", "search")
        if isinstance(intent, str):
            intent = IntentType(intent)

        return ParsedQuery(
            topic=data["topic"],
            keywords=data.get("keywords", []),
            region=data.get("region"),
            time_range=time_range,
            min_rows=data.get("min_rows"),
            format=data.get("format", []),
            license=lic,
            domain=data.get("domain", "other"),
            intent=intent,
            verify_url=data.get("verify_url"),
        )

    def _parse_url(self, url: str) -> ParsedQuery:
        """Construct a verify-intent ParsedQuery from a URL."""
        logger.info("Verifying dataset URL: %s", url)
        return ParsedQuery(
            topic="verification",
            keywords=[],
            domain="other",
            intent=IntentType.VERIFY,
            verify_url=url,
        )

    def _extract_year_range(self, query: str) -> TimeRange | None:
        """Try to extract year range from query text."""
        now = datetime.now().year
        match = YEAR_RANGE_PATTERN.search(query)
        if match:
            groups = match.groups()
            if groups[0] and groups[1]:
                return TimeRange(start=int(groups[0]), end=int(groups[1]))
            elif groups[2]:
                return TimeRange(start=now - int(groups[2]), end=now)
            elif groups[3]:
                return TimeRange(start=now - int(groups[3]), end=now)
        return None
