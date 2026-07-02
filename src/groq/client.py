import logging
import time

from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError

from src.config import get_settings
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)


class GroqClient:
    """Reusable AI client with support for both Groq and DS2API proxy backends.

    When ai_backend="proxy", uses AsyncOpenAI pointed at ds2api endpoint.
    When ai_backend="groq", uses AsyncOpenAI pointed at Groq API.
    Both use the same OpenAI-compatible interface.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.backend = settings.ai_backend

        if self.backend == "proxy":
            self.client = AsyncOpenAI(
                base_url=settings.proxy_base_url,
                api_key=settings.proxy_api_key,
            )
            self.primary_model = settings.proxy_model_primary
            self.fallback_model = settings.proxy_model_fallback
        else:
            self.client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
            )
            self.primary_model = settings.groq_model_primary
            self.fallback_model = settings.groq_model_fallback

        logger.info(
            "AI client initialized: backend=%s, model=%s",
            self.backend,
            self.primary_model,
        )

    async def parse_query(self, query: str, system_prompt: str) -> ParsedQuery:
        """Parse natural language query into structured ParsedQuery."""
        start = time.time()
        result: str = ""
        model_used: str = self.primary_model

        try:
            result = await self._call_ai(query, system_prompt, self.primary_model)
            model_used = self.primary_model
        except RateLimitError:
            logger.warning(
                "Rate limit on primary model (%s), falling back to %s",
                self.primary_model,
                self.fallback_model,
            )
            result = await self._call_ai(query, system_prompt, self.fallback_model)
            model_used = self.fallback_model
        except APIConnectionError as e:
            logger.error("Connection error (%s): %s", self.backend, e)
            raise
        except APIStatusError as e:
            logger.error("API error (%s): %s", self.backend, e)
            raise

        elapsed = int((time.time() - start) * 1000)
        parsed = ParsedQuery.model_validate_json(result)
        parsed.model_used = f"{self.backend}:{model_used}"
        parsed.parsing_time_ms = elapsed
        return parsed

    async def _call_ai(self, query: str, system_prompt: str, model: str) -> str:
        """Make a single async AI API call with JSON response format."""
        completion = await self.client.chat.completions.create(
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
            raise ValueError(f"AI ({self.backend}) returned empty response")
        return content
