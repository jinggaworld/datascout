"""Register DataScout agent with CROO Agent Store on startup."""

import logging
from typing import Any

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

# DataScout service definition for the CROO Agent Store
AGENT_SERVICE = {
    "name": "DataScout",
    "description": (
        "Automated dataset search, scoring & reporting agent. "
        "Searches 10+ open data sources simultaneously (HuggingFace, Kaggle, "
        "data.gov, World Bank, FRED, NOAA, OpenML, Zenodo, OpenAQ, arXiv), "
        "deduplicates, ranks by relevance, scores readiness, detects licenses, "
        "and delivers a structured report with citations."
    ),
    "capability": "dataset_search",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language dataset search query",
            },
            "topic": {
                "type": "string",
                "description": "Structured topic (alternative to query)",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional keywords for filtering",
            },
            "region": {
                "type": "string",
                "description": "Geographic region filter (country code or 'global')",
            },
            "domain": {
                "type": "string",
                "description": "Domain category: finance, health, climate, etc.",
            },
            "license": {
                "type": "string",
                "enum": ["any", "commercial_ok", "research_only"],
                "description": "License preference filter",
            },
            "min_rows": {
                "type": "integer",
                "description": "Minimum number of rows",
            },
        },
        "required": ["query"],
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "report": {"type": "object"},
            "markdown": {"type": "string"},
            "elapsed_ms": {"type": "integer"},
        },
    },
    "pricing": {
        "model": "per_query",
        "base_price_usdc": 0.01,
        "per_source_usdc": 0.002,
        "extras": {
            "time_range_filter": 0.005,
            "license_filter": 0.005,
            "min_rows_filter": 0.005,
        },
        "currency": "USDC",
    },
    "sla": {
        "max_response_time_sec": 60,
        "uptime_percent": 99.0,
    },
    "tags": [
        "dataset",
        "search",
        "data-discovery",
        "open-data",
        "research",
        "machine-learning",
        "data-profiling",
    ],
}


async def register_agent() -> dict[str, Any]:
    """Register DataScout agent with the CROO Agent Store.

    Returns the registration response from CROO, or an error dict.
    """
    settings = get_settings()

    if not settings.cap_agent_id or not settings.cap_sdk_key:
        logger.warning(
            "CAP_AGENT_ID or CAP_SDK_KEY not set — skipping CROO registration"
        )
        return {"status": "skipped", "reason": "missing credentials"}

    payload = {
        "agent_id": settings.cap_agent_id,
        "wallet": settings.cap_agent_wallet,
        "service": AGENT_SERVICE,
        "sdk_key": settings.cap_sdk_key,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Agent-ID": settings.cap_agent_id,
        "Authorization": f"Bearer {settings.cap_sdk_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.cap_api_url}/v1/agents/register",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                "Agent registered with CROO: agent_id=%s, status=%s",
                settings.cap_agent_id,
                data.get("status"),
            )
            return data
    except httpx.HTTPStatusError as e:
        logger.error(
            "CROO registration failed (HTTP %d): %s",
            e.response.status_code,
            e.response.text[:200],
        )
        return {"status": "error", "http_status": e.response.status_code}
    except httpx.ConnectError as e:
        logger.warning("CROO network unreachable: %s — agent will run locally", e)
        return {"status": "offline", "reason": str(e)}
    except Exception as e:
        logger.error("CROO registration error: %s", e)
        return {"status": "error", "reason": str(e)}


async def deregister_agent() -> dict[str, Any]:
    """Deregister agent from CROO on shutdown (graceful disconnect)."""
    settings = get_settings()

    if not settings.cap_agent_id or not settings.cap_sdk_key:
        return {"status": "skipped"}

    headers = {
        "X-Agent-ID": settings.cap_agent_id,
        "Authorization": f"Bearer {settings.cap_sdk_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.cap_api_url}/v1/agents/deregister",
                json={"agent_id": settings.cap_agent_id},
                headers=headers,
            )
            resp.raise_for_status()
            logger.info("Agent deregistered from CROO: %s", settings.cap_agent_id)
            return resp.json()
    except Exception as e:
        logger.warning("CROO deregistration failed (non-critical): %s", e)
        return {"status": "error", "reason": str(e)}
