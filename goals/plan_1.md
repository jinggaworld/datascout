# Plan 1: Project Setup & Architecture
**DataScout — CROO Agent Hackathon**

---

## Overview

Setup dasar proyek DataScout: struktur folder, dependencies, configuration management, dan environment setup. Ini adalah fondasi yang harus selesai sebelum semua plan lain bisa dimulai.

---

## Deliverables

1. **Project Structure** — Folder layout yang bersih dan scalable
2. **Python Package** — `pyproject.toml` / `requirements.txt` dengan semua dependencies
3. **Configuration Module** — Environment variables, API keys, settings management
4. **Docker Setup** — `Dockerfile` dan `docker-compose.yml` untuk reproducibility
5. **README.md** — Setup instructions, architecture overview, contributing guide
6. **Gitignore** — Proper `.gitignore` untuk Python project

---

## Project Structure

```
datascout/
├── goals/                    # Plans & documentation
│   ├── plan.md              # Master plan
│   ├── plan_1.md            # This file
│   ├── plan_2.md - plan_20.md
│   └── design.md            # UI/UX design system
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point & FastAPI app
│   ├── config.py            # Settings management (pydantic-settings)
│   ├── models/              # Pydantic data models
│   │   ├── __init__.py
│   │   ├── query.py         # ParsedQuery, TimeRange models
│   │   ├── dataset.py       # DatasetResult, DatasetMetadata
│   │   ├── report.py        # Report, Score, License models
│   │   └── cap.py           # CAP protocol models
│   ├── groq/                # Groq AI query parser
│   │   ├── __init__.py
│   │   ├── parser.py        # Main parser logic
│   │   ├── prompts.py       # System prompts
│   │   └── client.py        # Groq client wrapper
│   ├── adapters/            # Data source adapters
│   │   ├── __init__.py
│   │   ├── base.py          # BaseSearchAdapter ABC
│   │   ├── huggingface.py
│   │   ├── kaggle.py
│   │   ├── openml.py
│   │   ├── zenodo.py
│   │   ├── data_gov.py
│   │   ├── worldbank.py
│   │   ├── eurostat.py
│   │   ├── who.py
│   │   ├── fred.py
│   │   ├── noaa.py
│   │   ├── openaq.py
│   │   ├── arxiv.py
│   │   ├── core_api.py
│   │   ├── wikidata.py
│   │   ├── figshare.py
│   │   └── datacite.py
│   ├── engine/              # Core processing engines
│   │   ├── __init__.py
│   │   ├── orchestrator.py  # Parallel search orchestrator
│   │   ├── dedup.py         # Deduplication engine
│   │   ├── ranking.py       # Relevance ranking
│   │   ├── license.py       # License extraction
│   │   ├── profiler.py      # Data profiling
│   │   └── score.py         # Readiness score calculator
│   ├── report/              # Report generation
│   │   ├── __init__.py
│   │   ├── generator.py     # Main report generator
│   │   ├── citations.py     # Academic citation formatter
│   │   └── manifest.py      # Reproducible download manifest
│   ├── cache/               # Internal knowledge base
│   │   ├── __init__.py
│   │   ├── db.py            # SQLite/DuckDB wrapper
│   │   └── manager.py       # Cache read/write logic
│   └── cap/                 # CAP Protocol integration
│       ├── __init__.py
│       ├── client.py        # CAP SDK wrapper
│       ├── negotiation.py   # Price estimation
│       ├── deliver.py       # Output formatting
│       └── clear.py         # Settlement handler
├── frontend/                # React frontend (plan_20)
│   ├── package.json
│   ├── src/
│   └── public/
├── tests/                   # Test suite
│   ├── test_groq_parser.py
│   ├── test_adapters/
│   └── test_engine/
├── scripts/                 # Utility scripts
│   └── setup_dev.sh
├── pyproject.toml           # Python project config
├── requirements.txt         # Pinned dependencies
├── .env.example             # Environment variables template
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Dependencies (requirements.txt)

```
# Core
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.9.0
pydantic-settings==2.5.0

# Groq AI (Query Parser)
groq==0.11.0

# HTTP & Async
httpx==0.27.0
aiohttp==3.10.0

# Data Processing
pandas==2.2.0
ydata-profiling==4.10.0

# Deduplication & Ranking
sentence-transformers==3.2.0
faiss-cpu==1.8.0

# Database (Cache)
duckdb==1.1.0

# CAP Protocol
websockets==12.0

# Utilities
python-dotenv==1.0.0
python-magic==0.4.27

# Testing
pytest==8.3.0
pytest-asyncio==0.24.0
httpx==0.27.0

# Linting
ruff==0.6.0
mypy==1.11.0
```

---

## Configuration Module (config.py)

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Groq AI
    groq_api_key: str
    groq_model_primary: str = "llama-3.3-70b-versatile"
    groq_model_fallback: str = "llama-3.1-8b-instant"
    
    # CAP Protocol
    cap_api_url: str = "https://api.croo.network"
    cap_ws_url: str = "wss://api.croo.network/ws"
    cap_agent_id: str = ""
    cap_agent_wallet: str = ""
    
    # Database (Cache)
    db_path: str = "datascout.db"
    
    # API Keys (optional data sources)
    kaggle_username: Optional[str] = None
    kaggle_key: Optional[str] = None
    fred_api_key: Optional[str] = None
    noaa_api_key: Optional[str] = None
    core_api_key: Optional[str] = None
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Rate Limits
    max_concurrent_searches: int = 10
    request_timeout: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

---

## .env.example

```
# Groq AI (Required - get from console.groq.com)
GROQ_API_KEY=gsk_xxxxxxxxxxxxx

# CAP Protocol (Required for production)
CAP_AGENT_ID=datascout-agent-001
CAP_AGENT_WALLET=0x...

# Kaggle (Optional - get from kaggle.com/settings)
KAGGLE_USERNAME=
KAGGLE_KEY=

# FRED (Optional - get from fred.stlouisfed.org)
FRED_API_KEY=

# NOAA (Optional - get from ncdc.noaa.gov)
NOAA_API_KEY=

# CORE (Optional - get from core.ac.uk)
CORE_API_KEY=

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

---

## FastAPI App Entry Point (main.py)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings

app = FastAPI(
    title="DataScout API",
    description="Agent Pencari Dataset Otomatis dari Banyak Sumber Terbuka",
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

@app.get("/")
async def root():
    return {
        "name": "DataScout",
        "version": "0.1.0",
        "description": "Agent Pencari Dataset Otomatis",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## Implementation Steps

1. [x] Create project directory structure
2. [x] Write `pyproject.toml` and `requirements.txt`
3. [x] Create `.env.example` with all required/optional env vars
4. [x] Implement `config.py` with pydantic-settings
5. [x] Create `main.py` with FastAPI app
6. [x] Create `.gitignore` for Python
7. [x] Create `Dockerfile` and `docker-compose.yml`
8. [x] Write initial `README.md`
9. [x] Create `__init__.py` files for all packages
10. [ ] Verify setup: `pip install -r requirements.txt` passes
11. [ ] Verify: `python -m src.main` starts server
12. [ ] Verify: `pytest` runs (even with 0 tests)

---

## Acceptance Criteria

- [ ] `pip install -r requirements.txt` installs without errors
- [ ] `python -m src.main` starts FastAPI server on port 8000
- [ ] `GET /` returns DataScout info JSON
- [ ] `GET /health` returns `{"status": "healthy"}`
- [ ] `GET /docs` shows Swagger UI
- [ ] `GROQ_API_KEY` can be loaded from `.env`
- [ ] Docker builds and runs successfully
- [ ] All `__init__.py` files present
- [ ] `.gitignore` excludes `.env`, `__pycache__`, `*.pyc`, `.venv/`
