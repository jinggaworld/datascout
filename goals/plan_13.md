# Plan 13: Parallel Search Orchestrator
**DataScout — CROO Agent Hackathon**

---

## Overview

Engine yang mengoordinasikan pencarian paralel ke semua search adapters sekaligus. Satu query dikirim ke belasan API/registry secara concurrent untuk mempercepat hasil secara dramatis.

**Dependensi:** plan_5-12 (Semua Search Adapters)

---

## Deliverables

1. **Orchestrator** — `src/engine/orchestrator.py` — Main coordinator
2. **Adapter Registry** — Register & manage semua adapters
3. **Concurrency Manager** — asyncio.gather dengan timeout & error handling
4. **Result Aggregator** — Merge hasil dari semua adapters
5. **Graceful Degradation** — Jika 1 adapter gagal, yang lain tetap jalan

---

## Implementation

### `src/engine/orchestrator.py`

```python
import asyncio
import logging
from typing import List
from src.models.query import ParsedQuery
from src.models.dataset import DatasetResult
from src.adapters.base import BaseSearchAdapter

logger = logging.getLogger(__name__)

class SearchOrchestrator:
    def __init__(self):
        self.adapters: dict[str, BaseSearchAdapter] = {}
        self.timeout = 30  # seconds per adapter
    
    def register_adapter(self, name: str, adapter: BaseSearchAdapter):
        self.adapters[name] = adapter
    
    async def search_all(self, parsed_query: ParsedQuery, limit_per_source=20) -> List[DatasetResult]:
        """Execute parallel search across all registered adapters."""
        tasks = []
        for name, adapter in self.adapters.items():
            task = self._safe_search(name, adapter, parsed_query, limit_per_source)
            tasks.append(task)
        
        # Run all searches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten & filter
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Adapter failed: {result}")
        
        return all_results
    
    async def _safe_search(self, name, adapter, query, limit):
        """Search with timeout and error handling."""
        try:
            return await asyncio.wait_for(
                adapter.search(query, limit),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout on adapter {name}")
            return []
        except Exception as e:
            logger.error(f"Error on adapter {name}: {e}")
            return []

# Setup all adapters
orchestrator = SearchOrchestrator()
from src.adapters.huggingface import HuggingFaceAdapter
from src.adapters.kaggle import KaggleAdapter
from src.adapters.openml import OpenMLAdapter
from src.adapters.zenodo import ZenodoAdapter
from src.adapters.data_gov import DataGovAdapter
from src.adapters.worldbank import WorldBankAdapter
from src.adapters.eurostat import EurostatAdapter
from src.adapters.who import WHOAdapter
from src.adapters.fred import FREDAdapter
from src.adapters.noaa import NOAAAdapter
from src.adapters.openaq import OpenAQAdapter
from src.adapters.arxiv import ArXivAdapter
from src.adapters.core_api import CoreAdapter
from src.adapters.wikidata import WikidataAdapter

orchestrator.register_adapter("huggingface", HuggingFaceAdapter())
orchestrator.register_adapter("kaggle", KaggleAdapter())
orchestrator.register_adapter("openml", OpenMLAdapter())
orchestrator.register_adapter("zenodo", ZenodoAdapter())
orchestrator.register_adapter("data_gov", DataGovAdapter())
orchestrator.register_adapter("worldbank", WorldBankAdapter())
orchestrator.register_adapter("eurostat", EurostatAdapter())
orchestrator.register_adapter("who", WHOAdapter())
orchestrator.register_adapter("fred", FREDAdapter())
orchestrator.register_adapter("noaa", NOAAAdapter())
orchestrator.register_adapter("openaq", OpenAQAdapter())
orchestrator.register_adapter("arxiv", ArXivAdapter())
orchestrator.register_adapter("core", CoreAdapter())
orchestrator.register_adapter("wikidata", WikidataAdapter())
```

---

## API Endpoint

```python
@app.post("/api/v1/search")
async def search_datasets(input_data: dict):
    """Full search pipeline: parse → search → dedup → rank."""
    parser = QueryParser()
    parsed = await parser.parse(input_data)
    
    results = await orchestrator.search_all(parsed)
    
    return {
        "status": "success",
        "query": parsed.model_dump(),
        "total_results": len(results),
        "results": [r.model_dump() for r in results]
    }
```

---

## Implementation Steps

1. [ ] Create `src/engine/__init__.py`
2. [ ] Create `src/engine/orchestrator.py`
3. [ ] Register all 14 adapters
4. [ ] Implement graceful degradation
5. [ ] Add timeout handling
6. [ ] Test parallel execution
7. [ ] Measure total search time
8. [ ] Write integration tests

## Acceptance Criteria

- [ ] All 14 adapters run in parallel
- [ ] Single adapter failure doesn't break others
- [ ] Total search time < 30 seconds
- [ ] Results properly aggregated
- [ ] Timeout handling works
