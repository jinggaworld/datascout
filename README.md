# DataScout 🧠

**Agent Pencari, Penilai, dan Penyaji Dataset Otomatis dari Banyak Sumber Terbuka**

> CROO Agent Hackathon — Track: Research & Intelligence Agents

---

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/your-org/datascout.git
cd datascout
```

### 2. Environment Variables

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (free from console.groq.com)
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Server

```bash
python -m src.main
```

Server starts at `http://localhost:8000`

### 5. API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Docker

```bash
docker compose up --build
```

---

## Architecture

```
User Query (natural language)
    ↓
🧠 Groq API (Llama 3.3 70B) — Parse query → structured params
    ↓
Parallel Search (14+ adapters)
    ↓ HuggingFace, Kaggle, OpenML, Zenodo, data.gov, World Bank, ...
Deduplication (FAISS + Embeddings)
    ↓
Relevance Ranking
    ↓
License Classification
    ↓
Data Profiling (pandas)
    ↓
Readiness Score (0-100)
    ↓
Final Report (JSON + Markdown)
```

---

## Data Sources (14+)

| Category | Sources |
|---|---|
| ML/Research | HuggingFace, Kaggle, OpenML |
| Open Science | Zenodo, Figshare, DataCite |
| Government | data.gov, data.europa.eu |
| International | World Bank, Eurostat, WHO |
| Finance/Climate | FRED, NOAA, OpenAQ |
| Academic | arXiv, CORE, Wikidata |

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, Pydantic
- **AI Brain:** Groq API (Llama 3.3 70B) — free, ultra-fast
- **Search:** httpx, asyncio (parallel)
- **Ranking:** sentence-transformers, FAISS
- **Profiling:** pandas
- **Cache:** DuckDB
- **Frontend:** React + Tailwind CSS (plan_20)

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | API info |
| GET | `/health` | Health check |
| POST | `/api/v1/parse` | Parse natural language query |
| POST | `/api/v1/search` | Full search pipeline |

---

## License

MIT
