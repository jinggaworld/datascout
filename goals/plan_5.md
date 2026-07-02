# Plan 5: HuggingFace Dataset Search Adapter
**DataScout — CROO Agent Hackathon**

---

## Overview

Adapter untuk mencari dataset dari HuggingFace Datasets Hub — sumber terbesar dataset ML/NLP/Vision dari komunitas open-source.

**Dependensi:** plan_4 (Core Data Models)

---

## API Details

```
Endpoint: https://huggingface.co/api/datasets
Method: GET
Auth: None (public)
Rate Limit: ~500 requests/hour (unauthenticated)

Search: ?search=<query>&limit=<n>&sort=lastModified&direction=-1
Filter by tag: ?filter=<tag>
```

---

## Implementation

### `src/adapters/huggingface.py`

```python
import httpx
from src.models.dataset import DatasetResult, DatasetMetadata
from src.adapters.base import BaseSearchAdapter

class HuggingFaceAdapter(BaseSearchAdapter):
    BASE_URL = "https://huggingface.co/api/datasets"
    SOURCE_NAME = "huggingface"
    
    async def search(self, parsed_query, limit=20) -> list[DatasetResult]:
        params = {
            "search": " ".join(parsed_query.keywords),
            "limit": limit,
            "sort": "lastModified",
            "direction": -1,
        }
        # Add domain-specific tags if available
        if parsed_query.domain:
            params["filter"] = parsed_query.domain
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            datasets = resp.json()
        
        return [self._parse_dataset(d) for d in datasets]
    
    def _parse_dataset(self, raw: dict) -> DatasetResult:
        return DatasetResult(
            id=f"hf-{raw['id']}",
            title=raw.get("id", ""),
            description=raw.get("description", ""),
            source=self.SOURCE_NAME,
            source_url=f"https://huggingface.co/datasets/{raw['id']}",
            download_url=None,
            rows=raw.get("stats", {}).get("rows"),
            columns=raw.get("stats", {}).get("features"),
            file_size_mb=None,
            file_format="parquet",
            last_updated=raw.get("lastModified"),
            tags=raw.get("tags", []),
            domain="ml",
            region=None,
        )
```

---

## Implementation Steps

1. [ ] Create `src/adapters/base.py` — BaseSearchAdapter ABC
2. [ ] Create `src/adapters/huggingface.py`
3. [ ] Test with real queries
4. [ ] Handle pagination (limit/offset)
5. [ ] Map HuggingFace tags to DataScout domains
6. [ ] Write unit tests

---

## Acceptance Criteria

- [ ] Search returns DatasetResult list
- [ ] Handles empty results gracefully
- [ ] Rate limit respected
- [ ] Tags correctly mapped to domains
