# Plan 2: AI Query Parser (DeepSeek V4 Flash via ds2api)
**DataScout — CROO Agent Hackathon**

---

## Overview

Implementation of the AI brain using **DeepSeek V4 Flash** via ds2api proxy to convert user natural language queries into structured parameters (JSON) that can be processed by the search engine. This is the most critical component — all searches depend on the quality of this parsing.

**AI Backend:** ds2api proxy running at `http://127.0.0.1:5001` exposing OpenAI-compatible API
**Model:** `deepseek-v4-flash` (primary), `deepseek-v4-flash-nothinking` (fallback)
**Fallback:** Groq API `llama-3.3-70b-versatile` (configurable via `AI_BACKEND=groq`)

**Dependency:** plan_1 (Project Setup)

---

## Deliverables

1. **AI Client Wrapper** — `src/groq/client.py` — Reusable AsyncOpenAI client with retry, fallback model
2. **System Prompt** — `src/groq/prompts.py` — Optimized prompts for query parsing
3. **Query Parser** — `src/groq/parser.py` — Main logic: natural language → ParsedQuery
4. **Input Router** — Handle 3 input types: natural language, structured params, URL verification
5. **Tests** — Unit tests for parser with various query examples

---

## AI Configuration

```
Backend: DeepSeek V4 Flash via ds2api proxy (OpenAI-compatible)
Primary Model: deepseek-v4-flash
Fallback Model: deepseek-v4-flash-nothinking
Temperature: 0.1 (consistent output)
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
    SEARCH = "search"      # Find new datasets
    VERIFY = "verify"      # Verify a specific dataset
    COMPARE = "compare"    # Compare multiple datasets

class LicenseFilter(str, Enum):
    ANY = "any"
    COMMERCIAL_OK = "commercial_ok"
    RESEARCH_ONLY = "research_only"

class TimeRange(BaseModel):
    start: Optional[int] = Field(None, description="Start year")
    end: Optional[int] = Field(None, description="End year")

class ParsedQuery(BaseModel):
    topic: str = Field(..., description="Main topic of the dataset")
    keywords: List[str] = Field(default_factory=list, description="Related search terms")
    region: Optional[str] = Field(None, description="Region: country code or global")
    time_range: Optional[TimeRange] = None
    min_rows: Optional[int] = Field(None, description="Minimum number of rows")
    format: List[str] = Field(default_factory=list, description="Format: csv, json, parquet")
    license: LicenseFilter = LicenseFilter.ANY
    domain: str = Field(..., description="Domain: finance, health, climate, etc.")
    intent: IntentType = IntentType.SEARCH
    verify_url: Optional[str] = Field(None, description="URL for verification mode")
    model_used: str = Field(default="", description="AI model used for parsing")
    parsing_time_ms: int = Field(default=0, description="Parsing time in ms")
```

---

## Implementation Steps

1. [x] Create `src/models/query.py` with ParsedQuery, TimeRange, enums
2. [x] Create `src/groq/prompts.py` with system prompt
3. [x] Create `src/groq/client.py` with AsyncOpenAI client (proxy + Groq support)
4. [x] Create `src/groq/parser.py` with QueryParser
5. [x] Add `POST /api/v1/parse` endpoint to `main.py`
6. [x] Write unit tests for parser
7. [x] Test with real DeepSeek V4 Flash via ds2api proxy
8. [x] Verify JSON output is valid and matches schema

---

## Acceptance Criteria

- [x] `POST /api/v1/parse` accepts `{"query": "..."}` and returns structured ParsedQuery
- [x] `POST /api/v1/parse` accepts `{"topic": "...", "region": "..."}` and returns ParsedQuery directly
- [x] `POST /api/v1/parse` accepts `{"url": "https://..."}` and returns verify intent
- [x] Parser handles Indonesian and English queries
- [x] Fallback to smaller model works when primary is rate-limited
- [x] All test cases pass
- [x] Parsing time < 2 seconds (including AI API call)
