# Plan 7: OpenML Dataset Search Adapter
**DataScout — CROO Agent Hackathon**

---

## Overview

Adapter untuk mencari dataset dari OpenML — repositori dataset ML terstandarisasi dengan metadata kualitas lengkap. Gratis tanpa API key.

**Dependensi:** plan_4 (Core Data Models)

---

## API Details

```
Base URL: https://www.openml.org/api/v1/json/
Method: GET
Auth: None (public)

Search datasets: /data/list/data_name/<query>
Get dataset info: /data/<id>
List all: /data/list/limit/100/offset/0
```

---

## Implementation

### `src/adapters/openml.py`

```python
import httpx
from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult

class OpenMLAdapter(BaseSearchAdapter):
    BASE_URL = "https://www.openml.org/api/v1/json"
    SOURCE_NAME = "openml"
    
    async def search(self, parsed_query, limit=20) -> list[DatasetResult]:
        search_term = parsed_query.keywords[0] if parsed_query.keywords else parsed_query.topic
        url = f"{self.BASE_URL}/data/list/data_name/{search_term}/limit/{limit}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        
        datasets = data.get("data", {}).get("dataset", [])
        return [self._parse_dataset(d) for d in datasets]
    
    def _parse_dataset(self, raw: dict) -> DatasetResult:
        did = raw.get("did", "")
        return DatasetResult(
            id=f"openml-{did}",
            title=raw.get("name", ""),
            description=raw.get("description", ""),
            source=self.SOURCE_NAME,
            source_url=f"https://www.openml.org/d/{did}",
            download_url=f"https://www.openml.org/api/v1/json/data/{did}",
            rows=int(raw.get("NumberOfInstances", 0)) if raw.get("NumberOfInstances") else None,
            columns=int(raw.get("NumberOfFeatures", 0)) if raw.get("NumberOfFeatures") else None,
            file_format=raw.get("format", "ARFF"),
            tags=raw.get("tags", []),
            domain="ml",
        )
```

---

## Implementation Steps

1. [ ] Create `src/adapters/openml.py`
2. [ ] Handle XML/JSON response format variations
3. [ ] Map OpenML task types to domains
4. [ ] Test with real queries
5. [ ] Write unit tests

## Acceptance Criteria

- [ ] Returns DatasetResult list
- [ ] Handles missing fields gracefully
- [ ] No API key required
