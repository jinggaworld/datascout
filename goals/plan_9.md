# Plan 9: data.gov (Socrata) Dataset Search Adapter
**DataScout — CROO Agent Hackathon**

---

## Overview

Adapter untuk mencari dataset dari data.gov menggunakan Socrata Open Data API — sumber data pemerintah AS lintas sektor.

**Dependensi:** plan_4 (Core Data Models)

---

## API Details

```
Base URL: https://api.us.socrata.com/api/catalog/v1
Method: GET
Auth: None (public app token works, optional)
Rate Limit: ~1000 requests/hour

Search: ?q=<query>&domains=data.gov&limit=<n>
Filter: ?domains=data.gov&categories=<category>
```

---

## Implementation

### `src/adapters/data_gov.py`

```python
import httpx
from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult

class DataGovAdapter(BaseSearchAdapter):
    BASE_URL = "https://api.us.socrata.com/api/catalog/v1"
    SOURCE_NAME = "data_gov"
    
    async def search(self, parsed_query, limit=20) -> list[DatasetResult]:
        params = {
            "q": " ".join(parsed_query.keywords[:3]),
            "domains": "data.gov",
            "limit": min(limit, 100),
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        
        results = data.get("results", [])
        return [self._parse_result(r) for r in results]
    
    def _parse_result(self, raw: dict) -> DatasetResult:
        res = raw.get("resource", {})
        meta = raw.get("metadata", {})
        
        return DatasetResult(
            id=f"datagov-{raw.get('id', '')}",
            title=res.get("name", ""),
            description=res.get("description", ""),
            source=self.SOURCE_NAME,
            source_url=f"https://data.gov/dataset/{raw.get('id', '')}",
            download_url=res.get("download_url"),
            rows=res.get("download_count"),
            file_format=res.get("format", "unknown"),
            last_updated=meta.get("updated_at"),
            tags=[t.get("name") for t in raw.get("classification", {}).get("domain_category", [])],
            domain="government",
            region="US",
        )
```

---

## Implementation Steps

1. [ ] Create `src/adapters/data_gov.py`
2. [ ] Handle Socrata response structure
3. [ ] Map domain categories to DataScout domains
4. [ ] Test with real queries
5. [ ] Write unit tests

## Acceptance Criteria

- [ ] Returns DatasetResult list from data.gov
- [ ] Handles rate limits gracefully
- [ ] No API key required (optional app token)
