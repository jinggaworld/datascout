# Plan 17: Data Profiling Engine
**DataScout — CROO Agent Hackathon**

---

## Overview

Engine untuk membuat profil data: preview sample rows, schema/column list, statistik dasar, dan missing value analysis. Semua diproses secara lokal menggunakan pandas.

**Dependensi:** plan_4 (Core Data Models)

---

## Deliverables

1. **Data Profiler** — `src/engine/profiler.py` — Main profiling logic
2. **Schema Extractor** — Extract column names, types, descriptions
3. **Statistics Calculator** — Mean, median, min, max, std for numeric columns
4. **Missing Value Analyzer** — Percentage of null values per column
5. **Sample Generator** — Preview 5-10 sample rows

---

## Implementation

### `src/engine/profiler.py`

```python
import pandas as pd
from typing import Optional, Dict, Any
from src.models.dataset import DatasetResult, DataPreview, DataProfile

class DataProfiler:
    MAX_SAMPLE_ROWS = 10
    MAX_PREVIEW_SIZE_MB = 10  # Only download if < 10MB
    
    def profile(self, dataset: DatasetResult, sample_data: Optional[pd.DataFrame] = None) -> DatasetResult:
        """Add profiling info to dataset result."""
        if sample_data is None:
            return dataset  # Can't profile without data
        
        preview = self._create_preview(sample_data)
        profile = self._create_profile(sample_data)
        
        return dataset.model_copy(update={
            "preview": preview,
            "data_profile": profile,
        })
    
    def _create_preview(self, df: pd.DataFrame) -> DataPreview:
        """Create sample preview of data."""
        sample = df.head(self.MAX_SAMPLE_ROWS)
        
        columns = []
        for col in df.columns:
            columns.append({
                "name": col,
                "dtype": str(df[col].dtype),
                "sample_values": df[col].head(3).tolist(),
                "null_count": int(df[col].isnull().sum()),
                "null_percentage": round(df[col].isnull().mean() * 100, 2),
            })
        
        return DataPreview(
            columns=columns,
            sample_rows=sample.to_dict("records"),
            total_rows=len(df),
            total_columns=len(df.columns),
        )
    
    def _create_profile(self, df: pd.DataFrame) -> DataProfile:
        """Create statistical profile."""
        numeric_stats = {}
        categorical_stats = {}
        
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                numeric_stats[col] = {
                    "mean": round(float(df[col].mean()), 4) if not df[col].isnull().all() else None,
                    "median": round(float(df[col].median()), 4) if not df[col].isnull().all() else None,
                    "std": round(float(df[col].std()), 4) if not df[col].isnull().all() else None,
                    "min": float(df[col].min()) if not df[col].isnull().all() else None,
                    "max": float(df[col].max()) if not df[col].isnull().all() else None,
                    "null_count": int(df[col].isnull().sum()),
                }
            else:
                categorical_stats[col] = {
                    "unique_count": int(df[col].nunique()),
                    "top_values": df[col].value_counts().head(5).to_dict(),
                    "null_count": int(df[col].isnull().sum()),
                }
        
        # Missing value summary
        missing_summary = {
            "total_cells": int(df.size),
            "total_missing": int(df.isnull().sum().sum()),
            "missing_percentage": round(df.isnull().mean().mean() * 100, 2),
            "columns_with_missing": [col for col in df.columns if df[col].isnull().any()],
        }
        
        return DataProfile(
            numeric_stats=numeric_stats,
            categorical_stats=categorical_stats,
            missing_summary=missing_summary,
        )
```

---

## Usage in Pipeline

```python
# After search results are obtained
async def profile_datasets(results: List[DatasetResult]) -> List[DatasetResult]:
    profiler = DataProfiler()
    profiled = []
    
    for dataset in results:
        if dataset.download_url and dataset.file_size_mb < profiler.MAX_PREVIEW_SIZE_MB:
            try:
                df = pd.read_csv(dataset.download_url)
                profiled.append(profiler.profile(dataset, df))
            except Exception as e:
                logger.warning(f"Failed to profile {dataset.id}: {e}")
                profiled.append(dataset)
        else:
            profiled.append(dataset)
    
    return profiled
```

---

## Implementation Steps

1. [ ] Create `src/engine/profiler.py`
2. [ ] Implement schema extraction
3. [ ] Implement statistics calculation
4. [ ] Implement missing value analysis
5. [ ] Handle different file formats (CSV, JSON, Parquet)
6. [ ] Test with real datasets
7. [ ] Write unit tests

## Acceptance Criteria

- [ ] Correctly extracts column names and types
- [ ] Calculates accurate statistics for numeric columns
- [ ] Identifies missing values correctly
- [ ] Sample preview shows first 10 rows
- [ ] Handles large files gracefully (skip if > 10MB)
