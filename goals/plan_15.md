# Plan 15: Relevance Ranking Engine
**DataScout — CROO Agent Hackathon**

---

## Overview

Engine ranking yang mengurutkan hasil pencarian berdasarkan relevansi terhadap query user. Menggunakan cosine similarity antara query embedding dan dataset description embedding.

**Dependensi:** plan_2 (Groq AI Query Parser), plan_4 (Core Data Models)

---

## Ranking Factors

1. **Relevance Score (0-1)** — Cosine similarity query ↔ dataset description
2. **Freshness** — Dataset yang lebih baru dapat bonus
3. **Popularity** — Jumlah downloads/views jika tersedia
4. **Size** — Dataset yang cukup besar lebih berguna
5. **Documentation** — Dataset dengan deskripsi lengkap lebih baik

---

## Implementation

### `src/engine/ranking.py`

```python
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

class RankingEngine:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
    
    def rank(self, query: ParsedQuery, datasets: List[DatasetResult]) -> List[DatasetResult]:
        """Rank datasets by relevance to query."""
        if not datasets:
            return []
        
        # Create query text
        query_text = f"{query.topic} {' '.join(query.keywords)} {query.domain}"
        
        # Create dataset texts
        dataset_texts = [
            f"{d.title} {d.description[:300]} {' '.join(d.tags)}"
            for d in datasets
        ]
        
        # Compute embeddings
        query_emb = self.model.encode([query_text])
        dataset_embs = self.model.encode(dataset_texts)
        
        # Cosine similarity
        similarities = np.dot(dataset_embs, query_emb.T).flatten()
        
        # Apply additional factors
        for i, dataset in enumerate(datasets):
            base_score = float(similarities[i])
            
            # Freshness bonus (newer = better)
            freshness_bonus = self._freshness_score(dataset)
            
            # Size bonus
            size_bonus = self._size_score(dataset)
            
            # Documentation bonus
            doc_bonus = self._doc_score(dataset)
            
            # Final score (weighted)
            final_score = (
                base_score * 0.7 +
                freshness_bonus * 0.1 +
                size_bonus * 0.1 +
                doc_bonus * 0.1
            )
            
            datasets[i] = dataset.model_copy(update={
                "relevance_score": round(final_score, 4)
            })
        
        # Sort by relevance score
        return sorted(datasets, key=lambda d: d.relevance_score, reverse=True)
    
    def _freshness_score(self, dataset: DatasetResult) -> float:
        """Score based on last update date."""
        if not dataset.last_updated:
            return 0.5
        # Simple: more recent = higher score
        from datetime import datetime
        try:
            updated = datetime.fromisoformat(dataset.last_updated.replace("Z", "+00:00"))
            days_ago = (datetime.now().astimezone() - updated).days
            return max(0, 1 - (days_ago / 365))  # Decay over 1 year
        except:
            return 0.5
    
    def _size_score(self, dataset: DatasetResult) -> float:
        """Score based on dataset size."""
        if not dataset.rows:
            return 0.5
        # Log scale: bigger = better, with diminishing returns
        import math
        return min(1.0, math.log10(max(dataset.rows, 1)) / 8)  # 100M rows = 1.0
    
    def _doc_score(self, dataset: DatasetResult) -> float:
        """Score based on documentation quality."""
        score = 0.5  # Base
        if dataset.description and len(dataset.description) > 100:
            score += 0.2
        if dataset.tags and len(dataset.tags) > 2:
            score += 0.15
        if dataset.download_url:
            score += 0.15
        return min(1.0, score)
```

---

## API Endpoint

```python
@app.post("/api/v1/rank")
async def rank_results(query: ParsedQuery, results: List[DatasetResult]):
    engine = RankingEngine()
    ranked = engine.rank(query, results)
    return {
        "results": [r.model_dump() for r in ranked[:20]]
    }
```

---

## Implementation Steps

1. [ ] Create `src/engine/ranking.py`
2. [ ] Implement embedding-based relevance scoring
3. [ ] Add freshness, size, documentation bonuses
4. [ ] Tune weights (0.7/0.1/0.1/0.1)
5. [ ] Test ranking quality with sample queries
6. [ ] Write unit tests

## Acceptance Criteria

- [ ] Most relevant datasets ranked first
- [ ] Ranking considers multiple factors
- [ ] Processing time < 3 seconds for 500 datasets
- [ ] Ranking is deterministic
