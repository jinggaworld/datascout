# Plan 12: Academic APIs (arXiv, CORE, Wikidata)
**DataScout — CROO Agent Hackathon**

---

## Overview

Adapter untuk 3 sumber akademik: arXiv (paper riset), CORE (open access papers), dan Wikidata (metadata entitas). Sumber ini membantu menemukan dataset yang terkait dengan paper riset.

**Dependensi:** plan_4 (Core Data Models)

---

## 1. arXiv API

```
Base URL: http://export.arxiv.org/api/
Method: GET
Auth: None (public)
Rate Limit: ~1 request/3 seconds

Search: /query?search_query=all:<query>&start=0&max_results=20
```

### Implementation

```python
import xml.etree.ElementTree as ET
from src.adapters.base import BaseSearchAdapter

class ArXivAdapter(BaseSearchAdapter):
    BASE_URL = "http://export.arxiv.org/api"
    SOURCE_NAME = "arxiv"
    
    async def search(self, parsed_query, limit=20):
        search_query = " AND ".join(parsed_query.keywords[:3])
        params = {
            "search_query": f"all:{search_query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/query", params=params)
            resp.raise_for_status()
        
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        
        return [self._parse_entry(e, ns) for e in entries]
    
    def _parse_entry(self, entry, ns) -> DatasetResult:
        title = entry.find("atom:title", ns).text.strip()
        summary = entry.find("atom:summary", ns).text.strip()
        arxiv_id = entry.find("atom:id", ns).text.strip().split("/")[-1]
        links = entry.findall("atom:link", ns)
        pdf_link = next((l.get("href") for l in links if l.get("title") == "pdf"), None)
        
        return DatasetResult(
            id=f"arxiv-{arxiv_id}",
            title=title,
            description=summary[:500],
            source=self.SOURCE_NAME,
            source_url=f"https://arxiv.org/abs/{arxiv_id}",
            download_url=pdf_link,
            tags=[t.text for t in entry.findall("atom:category", ns)],
            domain="academic",
        )
```

---

## 2. CORE API

```
Base URL: https://api.core.ac.uk/v3/
Auth: API Key (free from core.ac.uk)

Search: /search/works?q=<query>&limit=<n>
Data: /search/data?query=<query>&limit=<n>
```

### Implementation

```python
class CoreAdapter(BaseSearchAdapter):
    BASE_URL = "https://api.core.ac.uk/v3"
    SOURCE_NAME = "core"
    
    def __init__(self):
        self.api_key = settings.core_api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
    
    async def search(self, parsed_query, limit=20):
        params = {
            "q": " ".join(parsed_query.keywords[:3]),
            "limit": limit,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/search/works",
                params=params,
                headers=self.headers
            )
            resp.raise_for_status()
            data = resp.json()
        
        results = data.get("results", [])
        return [self._parse_work(w) for w in results]
```

---

## 3. Wikidata API

```
Base URL: https://www.wikidata.org/w/
API: /api.php?action=wbsearchentities&search=<query>&language=en&format=json
SPARQL: https://query.wikidata.org/sparql
```

### Implementation

```python
class WikidataAdapter(BaseSearchAdapter):
    BASE_URL = "https://www.wikidata.org/w/api.php"
    SOURCE_NAME = "wikidata"
    
    async def search(self, parsed_query, limit=20):
        params = {
            "action": "wbsearchentities",
            "search": " ".join(parsed_query.keywords[:2]),
            "language": "en",
            "format": "json",
            "limit": limit,
            "type": "item",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        
        results = data.get("search", [])
        return [self._parse_entity(e) for e in results]
```

---

## Implementation Steps

1. [ ] Create `src/adapters/arxiv.py`
2. [ ] Create `src/adapters/core_api.py`
3. [ ] Create `src/adapters/wikidata.py`
4. [ ] Handle XML parsing for arXiv
5. [ ] Handle CORE API key
6. [ ] Test all three adapters
7. [ ] Write unit tests

## Acceptance Criteria

- [ ] arXiv returns paper results with dataset links
- [ ] CORE works with API key
- [ ] Wikidata returns entity metadata
- [ ] All return DatasetResult list
