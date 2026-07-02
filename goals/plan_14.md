# Plan 14: Smart Deduplication Engine
**DataScout — CROO Agent Hackathon**

---

## Overview

Engine deduplikasi cerdas yang mendeteksi dataset sama yang muncul di berbagai sumber (mis. dataset yang di-mirror di Kaggle DAN Zenodo), lalu menggabungkannya jadi satu entri dengan semua link sumbernya.

**Dependensi:** plan_4 (Core Data Models)

---

## Approach

Menggunakan **sentence-transformers** untuk embedding judul + deskripsi, lalu **FAISS** untuk cosine similarity search. Threshold konservatif untuk menghindari false positive.

---

## Implementation

### `src/engine/dedup.py`

```python
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List
from src.models.dataset import DatasetResult

class DeduplicationEngine:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.threshold = 0.85  # Konservatif — hindari false positive
        self.index = None
        self.datasets: List[DatasetResult] = []
    
    def deduplicate(self, datasets: List[DatasetResult]) -> List[DatasetResult]:
        """Remove duplicates and merge sources."""
        if not datasets:
            return []
        
        # Create embeddings
        texts = [f"{d.title} {d.description[:200]}" for d in datasets]
        embeddings = self.model.encode(texts)
        embeddings = embeddings.astype("float32")
        
        # Build FAISS index
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)  # Inner product for cosine sim
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        # Find duplicates
        merged = []
        seen = set()
        
        for i, dataset in enumerate(datasets):
            if i in seen:
                continue
            
            # Find similar datasets
            D, I = self.index.search(embeddings[i:i+1], k=10)
            similar_ids = [idx for idx, score in zip(I[0], D[0]) if score > self.threshold and idx != i]
            
            # Merge: keep best version, add all source URLs
            merged_dataset = self._merge_datasets(dataset, [datasets[j] for j in similar_ids if j not in seen])
            merged.append(merged_dataset)
            
            # Mark as seen
            seen.add(i)
            seen.update(similar_ids)
        
        return merged
    
    def _merge_datasets(self, primary: DatasetResult, duplicates: List[DatasetResult]) -> DatasetResult:
        """Merge duplicate datasets into one entry."""
        all_sources = [primary.source_url] + [d.source_url for d in duplicates]
        all_ids = [primary.id] + [d.id for d in duplicates]
        
        # Use best metadata (highest row count)
        best = primary
        for d in duplicates:
            if (d.rows or 0) > (best.rows or 0):
                best = d
        
        return best.model_copy(update={
            "merged_from": all_ids,
            "source_url": all_sources[0],  # Primary URL
        })
```

---

## API Endpoint

```python
@app.post("/api/v1/dedup")
async def dedup_results(results: List[DatasetResult]):
    """Deduplicate search results."""
    engine = DeduplicationEngine()
    deduped = engine.deduplicate(results)
    return {
        "original_count": len(results),
        "deduped_count": len(deduped),
        "results": [r.model_dump() for r in deduped]
    }
```

---

## Implementation Steps

1. [ ] Install sentence-transformers and faiss-cpu
2. [ ] Create `src/engine/dedup.py`
3. [ ] Implement embedding-based deduplication
4. [ ] Tune threshold (0.85 konservatif)
5. [ ] Implement merge logic
6. [ ] Test with datasets from multiple sources
7. [ ] Write unit tests

## Acceptance Criteria

- [ ] Detects same dataset across HuggingFace + Kaggle + Zenodo
- [ ] Merges into single entry with all source URLs
- [ ] No false positives (different datasets incorrectly merged)
- [ ] Handles empty input gracefully
- [ ] Processing time < 5 seconds for 1000 datasets
