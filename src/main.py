import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.groq.parser import QueryParser
from src.models.query import ParsedQuery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DataScout API",
    description="Agent Pencari, Penilai, dan Penyaji Dataset Otomatis dari Banyak Sumber Terbuka",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize parser (lazy — doesn't crash if GROQ_API_KEY missing at import time)
_parser: QueryParser | None = None


def get_parser() -> QueryParser:
    global _parser
    if _parser is None:
        _parser = QueryParser()
    return _parser


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "DataScout",
        "version": "0.1.0",
        "description": "Agent Pencari Dataset Otomatis dari Banyak Sumber Terbuka",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/api/v1/parse")
async def parse_query(input_data: dict[str, Any]) -> dict[str, Any]:
    """Parse user query into structured parameters.

    Accepts three input types:
    - {"query": "..."} — Natural language query (parsed via Groq AI)
    - {"topic": "...", "region": "..."} — Pre-structured params (used directly)
    - {"url": "https://..."} — Dataset URL for verification
    """
    try:
        parser = get_parser()
        parsed: ParsedQuery = await parser.parse(input_data)
        return {
            "status": "success",
            "parsed": parsed.model_dump(),
            "model_used": parsed.model_used,
            "parsing_time_ms": parsed.parsing_time_ms,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Parse error: %s", e)
        raise HTTPException(status_code=500, detail=f"Parse failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
