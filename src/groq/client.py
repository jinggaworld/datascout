import json
import logging
import time
from typing import Any

from groq import APIConnectionError, Groq, RateLimitError

from src.config import get_settings
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)


class GroqClient:
    """Reusable Groq API client with retry and fallback model support."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = Groq(api_key=settings.groq_api_key)
        self.primary_model = settings.groq_model_primary
        self.fallback_model = settings.groq_model_fallback
        self.max_retries = 2
        self.retry_delay = 1.0

    async def parse_query(self, query: str, system_prompt: str) -> ParsedQuery:
        """Parse natural language query into structured ParsedQuery."""
        start = time.time()
        result: str = ""
        model_used: str = self.primary_model

        try:
            result = await self._call_groq(query, system_prompt, self.primary_model)
            model_used = self.primary_model
        except RateLimitError:
            logger.warning(
                "Rate limit on primary model (%s), falling back to %s",
                self.primary_model,
                self.fallback_model,
            )
            result = await self._call_groq(query, system_prompt, self.fallback_model)
            model_used = self.fallback_model
        except APIConnectionError as e:
            logger.error("Groq connection error: %s", e)
            raise

        elapsed = int((time.time() - start) * 1000)
        parsed = ParsedQuery.model_validate_json(result)
        parsed.model_used = model_used
        parsed.parsing_time_ms = elapsed
        return parsed

    async def _call_groq(self, query: str, system_prompt: str, model: str) -> str:
        """Make a single Groq API call with JSON response format."""
        completion = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )
        content = completion.choices[0].message.content
        if content is None:
            raise ValueError("Groq returned empty response")
        return content
