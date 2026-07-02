# Plan 2: Groq AI Query Parser
**DataScout — CROO Agent Hackathon**

---

## Overview

Implementasi otak AI menggunakan Groq API untuk mengubah query bahasa natural dari user menjadi parameter terstruktur (JSON) yang bisa diproses oleh search engine. Ini adalah komponen paling kritis — semua pencarian bergantung pada kualitas parsing ini.

**Dependensi:** plan_1 (Project Setup)

---

## Deliverables

1. **Groq Client Wrapper** — `src/groq/client.py` — Reusable client dengan retry, rate limit handling, fallback model
2. **System Prompt** — `src/groq/prompts.py` — Optimized prompts untuk query parsing
3. **Query Parser** — `src/groq/parser.py` — Main logic: natural language → ParsedQuery
4. **Input Router** — Handle 3 input types: natural language, structured params, URL verification
5. **Tests** — Unit tests untuk parser dengan berbagai query examples

---

## Groq API Configuration

```
Primary Model: llama-3.3-70b-versatile (kompleks, multi-filter)
Fallback Model: llama-3.1-8b-instant (query sederhana, rate limit)
Temperature: 0.1 (konsistensi output)
Max Tokens: 1024
Response Format: json_object
```

---

## Data Models (src/models/query.py)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class IntentType(str, Enum):
    SEARCH = "search"      # Cari dataset baru
    VERIFY = "verify"      # Verifikasi dataset tertentu
    COMPARE = "compare"    # Bandingkan beberapa dataset

class LicenseFilter(str, Enum):
    ANY = "any"
    COMMERCIAL_OK = "commercial_ok"
    RESEARCH_ONLY = "research_only"

class TimeRange(BaseModel):
    start: Optional[int] = Field(None, description="Tahun mulai")
    end: Optional[int] = Field(None, description="Tahun selesai")

class ParsedQuery(BaseModel):
    topic: str = Field(..., description="Topik utama dataset")
    keywords: List[str] = Field(default_factory=list, description="Kata kunci terkait")
    region: Optional[str] = Field(None, description="Wilayah: country code atau global")
    time_range: Optional[TimeRange] = None
    min_rows: Optional[int] = Field(None, description="Minimum jumlah baris")
    format: List[str] = Field(default_factory=list, description="Format: csv, json, parquet")
    license: LicenseFilter = LicenseFilter.ANY
    domain: str = Field(..., description="Domain: finance, health, climate, dll")
    intent: IntentType = IntentType.SEARCH
    verify_url: Optional[str] = Field(None, description="URL untuk mode verifikasi")

# Response dari Groq yang di-parse
raw_response: str  # JSON string dari Groq
model_used: str    # Model yang dipakai
parsing_time_ms: int  # Waktu parsing dalam ms
```

---

## System Prompt (src/groq/prompts.py)

```
You are DataScout's query parser — an AI assistant that extracts structured dataset search parameters from natural language queries.

Your task: Parse the user's query about datasets into a valid JSON object with these fields:

- topic: string — Main subject of the dataset (e.g., "housing prices", "e-commerce fraud", "air quality")
- keywords: string[] — Related search terms (2-5 keywords)
- region: string|null — Geographical focus. Use ISO country codes (US, ID, EU, GB) or "global"
- time_range: object|null — {"start": year, "end": year} if mentioned
- min_rows: integer|null — Minimum dataset size (rows) if specified
- format: string[] — Preferred file formats. Default: []
- license: "commercial_ok" | "research_only" | "any" — License requirement. Default: "any"
- domain: string — Category: finance, health, climate, education, transport, energy, agriculture, social, technology, environment, government, other
- intent: "search" | "verify" | "compare"
- verify_url: string|null — URL if user wants to verify a specific dataset

Rules:
1. Always output valid JSON matching this schema exactly
2. If information is not specified, use null/empty defaults
3. For region, prefer ISO 3166-1 alpha-2 codes
4. For domain, use the most specific category that fits
5. Extract implicit requirements (e.g., "5 tahun terakhir" → time_range with end=current_year, start=current_year-5)
6. If the query is a URL, set intent="verify" and verify_url to the URL
7. If the query compares multiple datasets, set intent="compare"
```

---

## Groq Client Wrapper (src/groq/client.py)

```python
import time
import logging
from groq import Groq, APIConnectionError, RateLimitError
from src.config import settings
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.primary_model = settings.groq_model_primary
        self.fallback_model = settings.groq_model_fallback
    
    async def parse_query(self, query: str, system_prompt: str) -> ParsedQuery:
        """Parse natural language query into structured ParsedQuery."""
        start = time.time()
        
        try:
            result = await self._call_groq(query, system_prompt, self.primary_model)
        except RateLimitError:
            logger.warning("Rate limit on primary model, falling back")
            result = await self._call_groq(query, system_prompt, self.fallback_model)
        except APIConnectionError as e:
            logger.error(f"Groq connection error: {e}")
            raise
        
        elapsed = int((time.time() - start) * 1000)
        parsed = ParsedQuery.model_validate_json(result)
        parsed.parsing_time_ms = elapsed
        return parsed
    
    async def _call_groq(self, query: str, system_prompt: str, model: str) -> str:
        completion = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024
        )
        return completion.choices[0].message.content
```

---

## Input Router (src/groq/parser.py)

```python
import json
import re
from src.groq.client import GroqClient
from src.groq.prompts import QUERY_PARSER_PROMPT
from src.models.query import ParsedQuery, IntentType

class QueryParser:
    def __init__(self):
        self.client = GroqClient()
    
    async def parse(self, input_data: dict) -> ParsedQuery:
        """Route input to appropriate handler."""
        # Check input type
        if "query" in input_data:
            # Natural language query
            return await self._parse_natural(input_data["query"])
        elif "topic" in input_data:
            # Already structured params (from A2A agent)
            return ParsedQuery(**input_data)
        elif "url" in input_data:
            # Dataset verification mode
            return ParsedQuery(
                topic="verification",
                keywords=[],
                domain="other",
                intent=IntentType.VERIFY,
                verify_url=input_data["url"]
            )
        else:
            raise ValueError("Invalid input: must have 'query', 'topic', or 'url'")
    
    async def _parse_natural(self, query: str) -> ParsedQuery:
        return await self.client.parse_query(query, QUERY_PARSER_PROMPT)
```

---

## API Endpoint

```python
# In src/main.py
from src.groq.parser import QueryParser

parser = QueryParser()

@app.post("/api/v1/parse")
async def parse_query(input_data: dict):
    """Parse user query into structured parameters."""
    parsed = await parser.parse(input_data)
    return {
        "status": "success",
        "parsed": parsed.model_dump(),
        "model_used": parsed.model_used,
        "parsing_time_ms": parsed.parsing_time_ms
    }
```

---

## Test Cases

| Query | Expected Domain | Expected Intent |
|---|---|---|
| "cari dataset harga rumah di Indonesia 5 tahun terakhir" | finance | search |
| "dataset transaksi e-commerce untuk deteksi fraud" | finance | search |
| "dataset kualitas udara kota besar minimal 10 ribu baris" | environment | search |
| "https://huggingface.co/datasets/xyz → verify dataset" | other | verify |
| "bandingkan dataset cuaca Indonesia vs Malaysia" | climate | compare |
| "dataset kesehatan mental mahasiswa Indonesia boleh komersial" | health | search |

---

## Implementation Steps

1. [ ] Create `src/groq/__init__.py`
2. [ ] Create `src/models/query.py` with ParsedQuery, TimeRange, enums
3. [ ] Create `src/groq/prompts.py` with system prompt
4. [ ] Create `src/groq/client.py` with GroqClient wrapper
5. [ ] Create `src/groq/parser.py` with QueryParser
6. [ ] Add `/api/v1/parse` endpoint to `main.py`
7. [ ] Write unit tests for parser
8. [ ] Test with real Groq API key
9. [ ] Verify JSON output is valid and matches schema
10. [ ] Test fallback model when rate limited

---

## Acceptance Criteria

- [ ] `POST /api/v1/parse` accepts `{"query": "..."}` and returns structured ParsedQuery
- [ ] `POST /api/v1/parse` accepts `{"topic": "...", "region": "..."}` and returns ParsedQuery directly
- [ ] `POST /api/v1/parse` accepts `{"url": "https://..."}` and returns verify intent
- [ ] Parser handles Indonesian and English queries
- [ ] Fallback to smaller model works when primary is rate-limited
- [ ] All test cases pass
- [ ] Parsing time < 2 seconds (including Groq API call)
