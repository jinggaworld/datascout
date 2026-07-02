# Plan 6: Kaggle Dataset Search Adapter
**DataScout — CROO Agent Hackathon**

---

## Overview

Adapter untuk mencari dataset dari Kaggle — platform terbesar dataset kompetisi dan komunitas data science.

**Dependensi:** plan_4 (Core Data Models)

---

## API Details

```
Kaggle uses CLI/internal API — no public REST search endpoint.
Requires: KAGGLE_USERNAME + KAGGLE_KEY (free from kaggle.com/settings)

Python SDK: pip install kaggle
CLI: kaggle datasets list -s "search_term" --csv
```

---

## Implementation

### `src/adapters/kaggle.py`

```python
import subprocess
import csv
import io
import os
from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult

class KaggleAdapter(BaseSearchAdapter):
    SOURCE_NAME = "kaggle"
    
    async def search(self, parsed_query, limit=20) -> list[DatasetResult]:
        # Kaggle CLI search
        search_term = "+".join(parsed_query.keywords[:3])
        cmd = [
            "kaggle", "datasets", "list",
            "-s", search_term,
            "--csv",
            "-p", str(limit)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"Kaggle CLI error: {result.stderr}")
        
        reader = csv.DictReader(io.StringIO(result.stdout))
        return [self._parse_row(row) for row in reader]
    
    def _parse_row(self, row: dict) -> DatasetResult:
        ref = row.get("ref", "")
        return DatasetResult(
            id=f"kaggle-{ref}",
            title=row.get("name", ref),
            description=row.get("subtitle", ""),
            source=self.SOURCE_NAME,
            source_url=f"https://www.kaggle.com/datasets/{ref}",
            download_url=f"https://www.kaggle.com/api/v1/datasets/download/{ref}",
            rows=int(row.get("totalBytes", 0)) // 1000 if row.get("totalBytes") else None,
            file_size_mb=float(row.get("totalBytes", 0)) / 1_000_000 if row.get("totalBytes") else None,
            file_format=row.get("fileType", "csv"),
            last_updated=row.get("lastUpdated"),
            tags=row.get("tags", []).split(",") if row.get("tags") else [],
            domain="data-science",
            region=None,
        )
```

---

## Implementation Steps

1. [ ] Create `src/adapters/kaggle.py`
2. [ ] Ensure Kaggle CLI is installed and configured
3. [ ] Test with search queries
4. [ ] Handle missing KAGGLE credentials gracefully
5. [ ] Parse CSV output correctly
6. [ ] Write unit tests

---

## Acceptance Criteria

- [ ] Search returns DatasetResult list from Kaggle
- [ ] Graceful fallback if Kaggle credentials not configured
- [ ] Correct parsing of Kaggle CLI output
