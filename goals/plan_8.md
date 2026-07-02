# Plan 8: Zenodo Dataset Search Adapter
**DataScout — CROO Agent Hackathon**

---

## Overview

Adapter untuk mencari dataset dari Zenodo — platform open science untuk riset ilmiah lintas bidang. Gratis, publik, well-documented API.

**Dependensi:** plan_4 (Core Data Models)

---

## API Details

```
Base URL: https://zenodo.org/api/
Search: GET /records?q=<query>&page=<n>&size=<20>
Auth: None (public)
Rate Limit: ~100 requests/minute
```

---

## Implementation

### `src/adapters/zenodo.py`

```python
import httpx
from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult

class ZenodoAdapter(BaseSearchAdapter):
    BASE_URL = "https://zenodo.org/api/records"
    SOURCE_NAME = "zenodo"
    
    async def search(self, parsed_query, limit=20) -> list[DatasetResult]:
        params = {
            "q": " ".join(parsed_query.keywords[:3]),
            "size": min(limit, 100),
            "page": 1,
            "type": "dataset",
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        
        hits = data.get("hits", {}).get("hits", [])
        return [self._parse_hit(h) for h in hits]
    
    def _parse_hit(self, hit: dict) -> DatasetResult:
        metadata = hit.get("metadata", {})
        files = hit.get("files", [])
        download_url = files[0]["links"]["self"] if files else None
        
        # Parse license
        license_info = metadata.get("license", "unknown")
        
        return DatasetResult(
            id=f"zenodo-{hit.get('id', '')}",
            title=metadata.get("title", ""),
            description=metadata.get("description", ""),
            source=self.SOURCE_NAME,
            source_url=f"https://zenodo.org/record/{hit.get('id', '')}",
            download_url=download_url,
            file_size_mb=files[0].get("size", 0) / 1_000_000 if files else None,
            last_updated=hit.get("created"),
            tags=[t.get("tag") for t in metadata.get("keywords", [])],
            domain="research",
            region=metadata.get("dates", [{}])[0].get("type") if metadata.get("dates") else None,
        )
```

---

## Implementation Steps

1. [ ] Create `src/adapters/zenodo.py`
2. [ ] Parse Zenodo record structure correctly
3. [ ] Extract DOI from metadata
4. [ ] Handle multi-file datasets
5. [ ] Test with real queries
6. [ ] Write unit tests

## Acceptance Criteria

- [ ] Returns DatasetResult list
- [ ] DOI extracted correctly
- [ ] License info parsed from Zenodo metadata
