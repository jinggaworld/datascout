# Plan 18: Readiness Score Calculator
**DataScout — CROO Agent Hackathon**

---

## Overview

Engine untuk menghitung skor kesiapan-pakai (readiness score) per dataset. Skor ini membantu user memutuskan dataset mana yang paling siap digunakan.

**Dependensi:** plan_16 (License Extraction), plan_17 (Data Profiling)

---

## Scoring Methodology

Skor dihitung dari 5 komponen (total 100 poin):

| Komponen | Bobot | Faktor |
|---|---|---|
| **Completeness** | 30% | Kelengkapan data, missing values rendah |
| **Freshness** | 20% | Tanggal update terakhir (semakin baru semakin baik) |
| **Size** | 20% | Jumlah baris (semakin besar semakin berguna) |
| **Documentation** | 15% | Kelengkapan deskripsi, tags, README |
| **License Clarity** | 15% | Jelas dan mengizinkan penggunaan yang diinginkan |

---

## Implementation

### `src/engine/score.py`

```python
from datetime import datetime
from typing import List
from src.models.dataset import DatasetResult
from src.models.score import ReadinessScore, ScoreBreakdown

class ReadinessCalculator:
    WEIGHTS = {
        "completeness": 0.30,
        "freshness": 0.20,
        "size": 0.20,
        "documentation": 0.15,
        "license": 0.15,
    }
    
    def calculate(self, dataset: DatasetResult) -> DatasetResult:
        """Calculate readiness score for a dataset."""
        breakdown = ScoreBreakdown(
            completeness=self._completeness_score(dataset),
            freshness=self._freshness_score(dataset),
            size=self._size_score(dataset),
            documentation=self._documentation_score(dataset),
            license=self._license_score(dataset),
        )
        
        # Weighted sum
        total = (
            breakdown.completeness * self.WEIGHTS["completeness"] +
            breakdown.freshness * self.WEIGHTS["freshness"] +
            breakdown.size * self.WEIGHTS["size"] +
            breakdown.documentation * self.WEIGHTS["documentation"] +
            breakdown.license * self.WEIGHTS["license"]
        )
        
        score = ReadinessScore(
            total=round(total * 100, 1),  # 0-100 scale
            breakdown=breakdown,
            grade=self._get_grade(total * 100),
        )
        
        return dataset.model_copy(update={"readiness_score": score})
    
    def _completeness_score(self, d: DatasetResult) -> float:
        """Score based on data completeness."""
        if not d.data_profile:
            return 0.5  # Unknown
        missing_pct = d.data_profile.missing_summary["missing_percentage"]
        return max(0, 1 - (missing_pct / 100))
    
    def _freshness_score(self, d: DatasetResult) -> float:
        if not d.last_updated:
            return 0.5
        try:
            updated = datetime.fromisoformat(d.last_updated.replace("Z", "+00:00"))
            days_ago = (datetime.now().astimezone() - updated).days
            return max(0, 1 - (days_ago / 365))
        except:
            return 0.5
    
    def _size_score(self, d: DatasetResult) -> float:
        import math
        if not d.rows:
            return 0.5
        return min(1.0, math.log10(max(d.rows, 1)) / 8)
    
    def _documentation_score(self, d: DatasetResult) -> float:
        score = 0.3  # Base
        if d.description and len(d.description) > 100:
            score += 0.3
        if d.tags and len(d.tags) > 2:
            score += 0.2
        if d.download_url:
            score += 0.2
        return min(1.0, score)
    
    def _license_score(self, d: DatasetResult) -> float:
        if not d.license_status:
            return 0.3
        if d.license_status.license_type == "commercial_ok":
            return 1.0
        elif d.license_status.license_type == "research_only":
            return 0.6
        elif d.license_status.needs_verification:
            return 0.3
        return 0.5
    
    def _get_grade(self, score: float) -> str:
        if score >= 80: return "A"
        elif score >= 60: return "B"
        elif score >= 40: return "C"
        elif score >= 20: return "D"
        return "F"
```

---

## API Endpoint

```python
@app.post("/api/v1/score")
async def score_datasets(results: List[DatasetResult]):
    calculator = ReadinessCalculator()
    scored = [calculator.calculate(d) for d in results]
    # Sort by score
    scored.sort(key=lambda d: d.readiness_score.total, reverse=True)
    return {"results": [r.model_dump() for r in scored]}
```

---

## Implementation Steps

1. [ ] Create `src/models/score.py` — ReadinessScore, ScoreBreakdown
2. [ ] Create `src/engine/score.py`
3. [ ] Implement all 5 scoring components
4. [ ] Tune weights
5. [ ] Add grade system (A-F)
6. [ ] Test with various dataset qualities
7. [ ] Write unit tests

## Acceptance Criteria

- [ ] Score range is 0-100
- [ ] All 5 components contribute to final score
- [ ] Grade system works (A ≥ 80, B ≥ 60, etc.)
- [ ] Datasets with better quality get higher scores
- [ ] Handles missing metadata gracefully
