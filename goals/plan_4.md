# Plan 4: Core Data Models & Schemas
**DataScout — CROO Agent Hackathon**

---

## Overview

Definisi semua data models (Pydantic) yang digunakan di seluruh sistem. Ini adalah kontrak data yang memastikan semua komponen bisa saling berkomunikasi.

**Dependensi:** plan_1 (Project Setup)

---

## Models to Create

### 1. Query Models (`src/models/query.py`)
- `ParsedQuery` — Output dari Groq parser
- `TimeRange` — Rentang waktu
- `IntentType` — Enum: search, verify, compare
- `LicenseFilter` — Enum: any, commercial_ok, research_only

### 2. Dataset Models (`src/models/dataset.py`)
- `DatasetResult` — Satu hasil dataset dari search
- `DatasetMetadata` — Metadata lengkap dataset
- `DataPreview` — Preview data (sample rows, schema)
- `DataProfile` — Statistik: missing values, column types
- `SearchResult` — Aggregated results dari semua sources

### 3. Score Models (`src/models/score.py`)
- `ReadinessScore` — Skor kesiapan-pakai (0-100)
- `ScoreBreakdown` — Detail komponen skor
- `RelevanceScore` — Skor relevansi terhadap query

### 4. License Models (`src/models/license.py`)
- `LicenseStatus` — Status lisensi terstruktur
- `LicenseEnum` — Enum lisensi umum

### 5. Report Models (`src/models/report.py`)
- `FinalReport` — Laporan akhir untuk buyer
- `DatasetComparison` — Tabel perbandingan
- `Citation` — Sitasi akademik
- `Manifest` — Manifest unduhan reproducible

### 6. CAP Models (`src/models/cap.py`)
- `CapOrder` — Order dari CAP
- `CapDelivery` — Delivery output
- `CapSettlement` — Settlement result

---

## DatasetResult Schema

```python
class DatasetResult(BaseModel):
    id: str                           # Unique ID
    title: str                        # Judul dataset
    description: str                  # Deskripsi
    source: str                       # Sumber: huggingface, kaggle, etc.
    source_url: str                   # URL di sumber asli
    download_url: Optional[str]       # Direct download link
    
    # Metadata
    rows: Optional[int]               # Jumlah baris
    columns: Optional[int]            # Jumlah kolom
    file_size_mb: Optional[float]     # Ukuran file
    file_format: Optional[str]        # csv, json, parquet, etc.
    last_updated: Optional[str]       # Tanggal update terakhir
    
    # Scores
    relevance_score: float            # 0-1
    readiness_score: float            # 0-100
    
    # License
    license_status: LicenseStatus
    
    # Preview
    preview: Optional[DataPreview]
    
    # Tags & Domain
    tags: List[str] = []
    domain: str
    region: Optional[str]
    
    # Dedup
    merged_from: List[str] = []       # Source IDs if merged
    
    class Config:
        frozen = True
```

---

## Implementation Steps

1. [ ] Create `src/models/__init__.py`
2. [ ] Create `src/models/query.py`
3. [ ] Create `src/models/dataset.py`
4. [ ] Create `src/models/score.py`
5. [ ] Create `src/models/license.py`
6. [ ] Create `src/models/report.py`
7. [ ] Create `src/models/cap.py`
8. [ ] Add model validation tests
9. [ ] Ensure all models have proper JSON Schema export

---

## Acceptance Criteria

- [ ] All models pass Pydantic validation
- [ ] JSON Schema export works for all models
- [ ] Models are importable from all other modules
- [ ] No circular imports
- [ ] All fields have proper type hints and descriptions
