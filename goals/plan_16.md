# Plan 16: License Extraction & Classification
**DataScout — CROO Agent Hackathon**

---

## Overview

Engine untuk mengekstrak dan mengklasifikasi status lisensi dari metadata dataset. Menggunakan regex pattern matching untuk frasa lisensi umum (CC0, CC-BY, MIT, ODbL, dll).

**Dependensi:** plan_4 (Core Data Models)

---

## License Classification

```
COMMERCIAL_OK:
  - CC0 (Public Domain)
  - CC-BY (Attribution)
  - CC-BY-SA (Attribution-ShareAlike)
  - MIT
  - Apache 2.0
  - Unlicense
  - ODbL

RESEARCH_ONLY:
  - CC-BY-NC (NonCommercial)
  - CC-BY-NC-SA
  - CC-BY-ND (NoDerivatives)
  - CC-BY-NC-ND

UNKNOWN:
  - No license specified
  - Custom/proprietary license
  - Ambiguous terms
```

---

## Implementation

### `src/engine/license.py`

```python
import re
from typing import Optional
from src.models.dataset import DatasetResult
from src.models.license import LicenseStatus, LicenseType

class LicenseExtractor:
    # Pattern matching for common licenses
    PATTERNS = {
        "CC0": [r"CC0", r"Public Domain", r"No Rights Reserved"],
        "CC-BY": [r"CC-BY(?![-]|\s*-)", r"Creative Commons Attribution(?![-]|\s*-)"],
        "CC-BY-SA": [r"CC-BY-SA", r"Attribution-ShareAlike"],
        "CC-BY-NC": [r"CC-BY-NC(?![-]|\s*-)", r"NonCommercial", r"Non-Commercial"],
        "CC-BY-NC-SA": [r"CC-BY-NC-SA"],
        "CC-BY-ND": [r"CC-BY-ND(?![-]|\s*-)", r"NoDerivatives"],
        "CC-BY-NC-ND": [r"CC-BY-NC-ND"],
        "MIT": [r"\bMIT\b License", r"MIT License"],
        "Apache": [r"Apache 2\.0", r"Apache License"],
        "ODbL": [r"ODbL", r"Open Database License"],
        "Unlicense": [r"Unlicense"],
    }
    
    COMMERCIAL_OK = {"CC0", "CC-BY", "CC-BY-SA", "MIT", "Apache", "ODbL", "Unlicense"}
    RESEARCH_ONLY = {"CC-BY-NC", "CC-BY-NC-SA", "CC-BY-ND", "CC-BY-NC-ND"}
    
    def extract(self, dataset: DatasetResult) -> DatasetResult:
        """Extract and classify license from dataset metadata."""
        # Check all text fields for license patterns
        text = f"{dataset.description} {dataset.title} {' '.join(dataset.tags)}"
        
        detected = self._detect_license(text)
        
        if detected in self.COMMERCIAL_OK:
            status = LicenseStatus(
                detected=True,
                license_type=LicenseType.COMMERCIAL_OK,
                license_name=detected,
                needs_verification=False,
            )
        elif detected in self.RESEARCH_ONLY:
            status = LicenseStatus(
                detected=True,
                license_type=LicenseType.RESEARCH_ONLY,
                license_name=detected,
                needs_verification=False,
            )
        else:
            status = LicenseStatus(
                detected=False,
                license_type=LicenseType.UNKNOWN,
                license_name=None,
                needs_verification=True,
            )
        
        return dataset.model_copy(update={"license_status": status})
    
    def _detect_license(self, text: str) -> Optional[str]:
        for license_name, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return license_name
        return None
```

---

## API Endpoint

```python
@app.post("/api/v1/license")
async def extract_licenses(results: List[DatasetResult]):
    extractor = LicenseExtractor()
    classified = [extractor.extract(d) for d in results]
    return {"results": [r.model_dump() for r in classified]}
```

---

## Implementation Steps

1. [ ] Create `src/models/license.py` — LicenseStatus, LicenseType
2. [ ] Create `src/engine/license.py`
3. [ ] Implement regex patterns for all license types
4. [ ] Test with datasets from various sources
5. [ ] Handle edge cases (mixed licenses, no license)
6. [ ] Write unit tests

## Acceptance Criteria

- [ ] Correctly identifies CC0, CC-BY, MIT, Apache, ODbL
- [ ] Correctly identifies CC-BY-NC as research-only
- [ ] Unknown licenses marked for manual verification
- [ ] No false positives
