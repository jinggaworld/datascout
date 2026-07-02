# Plan 19: Report Generator & Manifest
**DataScout — CROO Agent Hackathon**

---

## Overview

Engine untuk menyusun laporan akhir: ranking dataset, tabel perbandingan, sitasi akademik otomatis, dan manifest unduhan reproducible. Output dalam format JSON (untuk agent lain) dan Markdown (untuk manusia).

**Dependensi:** plan_18 (Readiness Score Calculator)

---

## Deliverables

1. **Report Generator** — `src/report/generator.py` — Main report builder
2. **Citation Formatter** — `src/report/citations.py` — Academic citation generator
3. **Manifest Builder** — `src/report/manifest.py` — Reproducible download manifest
4. **Output Formats** — JSON (API) + Markdown (human-readable)

---

## Final Report Schema

```python
class FinalReport(BaseModel):
    query: ParsedQuery           # Original parsed query
    timestamp: str               # ISO timestamp
    total_sources_searched: int  # Number of APIs queried
    total_results_found: int    # Total raw results
    deduped_results: int        # After deduplication
    
    # Top datasets
    top_datasets: List[DatasetResult]  # Top 20 ranked datasets
    comparison_table: Optional[DatasetComparison]  # Side-by-side comparison
    
    # Summary
    summary: str               # AI-generated summary of findings
    domain_distribution: Dict[str, int]  # Results by domain
    source_distribution: Dict[str, int]  # Results by source
    
    # Citations
    citations: List[Citation]  # Academic citations for top datasets
    
    # Manifest
    manifest: Manifest         # Reproducible download manifest
    
    # CAP
    hash_proof: str            # Hash bukti pengerjaan
```

---

## Citation Formatter

### `src/report/citations.py`

```python
from src.models.dataset import DatasetResult
from src.models.report import Citation
from datetime import datetime

class CitationFormatter:
    def format_citation(self, dataset: DatasetResult) -> Citation:
        """Generate APA-style citation for a dataset."""
        year = datetime.now().year
        if dataset.last_updated:
            try:
                year = datetime.fromisoformat(dataset.last_updated).year
            except:
                pass
        
        # APA format: Author. (Year). Title. Source. URL
        author = self._get_author(dataset)
        title = dataset.title
        source = dataset.source.replace("_", " ").title()
        url = dataset.source_url
        
        apa = f"{author}. ({year}). {title}. {source}. {url}"
        
        return Citation(
            dataset_id=dataset.id,
            apa=apa,
            bibtex=self._to_bibtex(dataset, author, year),
        )
    
    def _get_author(self, dataset: DatasetResult) -> str:
        if dataset.source == "huggingface":
            return dataset.title.split("/")[0] if "/" in dataset.title else "DataScout"
        elif dataset.source == "zenodo":
            return dataset.title.split("/")[0] if "/" in dataset.title else "DataScout"
        return "DataScout"
    
    def _to_bibtex(self, dataset, author, year) -> str:
        key = dataset.id.replace("-", "_")
        return f"@misc{{{key},\n  author = {{{author}}},\n  year = {{{year}}},\n  title = {{{dataset.title}}},\n  url = {{{dataset.source_url}}},\n}}"
```

---

## Manifest Builder

### `src/report/manifest.py`

```python
import hashlib
import json
from src.models.dataset import DatasetResult
from src.models.report import Manifest, ManifestEntry

class ManifestBuilder:
    def build(self, datasets: List[DatasetResult]) -> Manifest:
        """Build reproducible download manifest."""
        entries = []
        for d in datasets:
            entry = ManifestEntry(
                dataset_id=d.id,
                title=d.title,
                source=d.source,
                download_url=d.download_url,
                source_url=d.source_url,
                file_format=d.file_format,
                checksum_algorithm="sha256",
                download_command=self._generate_download_cmd(d),
            )
            entries.append(entry)
        
        # Generate manifest hash
        manifest_json = json.dumps([e.model_dump() for e in entries], sort_keys=True)
        manifest_hash = hashlib.sha256(manifest_json.encode()).hexdigest()
        
        return Manifest(
            version="1.0",
            generator="DataScout",
            datasets=entries,
            manifest_hash=manifest_hash,
        )
    
    def _generate_download_cmd(self, dataset: DatasetResult) -> str:
        if not dataset.download_url:
            return "# No download URL available"
        
        if dataset.source == "huggingface":
            return f"huggingface-cli download {dataset.title}"
        elif dataset.source == "kaggle":
            return f"kaggle datasets download -d {dataset.title}"
        else:
            return f"wget {dataset.download_url}"
```

---

## Markdown Report Generator

```python
def generate_markdown(report: FinalReport) -> str:
    md = f"""# DataScout Report

**Query:** {report.query.topic}
**Keywords:** {', '.join(report.query.keywords)}
**Region:** {report.query.region or 'Global'}
**Date:** {report.timestamp}

---

## Summary

Searched **{report.total_sources_searched}** sources, found **{report.total_results_found}** datasets, **{report.deduped_results}** after deduplication.

## Top Datasets

"""
    
    for i, d in enumerate(report.top_datasets[:10], 1):
        md += f"""
### {i}. {d.title}

- **Source:** {d.source}
- **Readiness Score:** {d.readiness_score.total}/100 ({d.readiness_score.grade})
- **License:** {d.license_status.license_name or 'Unknown'}
- **URL:** {d.source_url}
- **Description:** {d.description[:200]}...
"""
    
    md += """
## Citations

"""
    for c in report.citations[:5]:
        md += f"```
{c.apa}
```
\n"
    
    return md
```

---

## Implementation Steps

1. [ ] Create `src/report/__init__.py`
2. [ ] Create `src/models/report.py` — FinalReport, Citation, Manifest models
3. [ ] Create `src/report/generator.py`
4. [ ] Create `src/report/citations.py`
5. [ ] Create `src/report/manifest.py`
6. [ ] Implement Markdown report generation
7. [ ] Generate hash proof for CAP
8. [ ] Test with sample data
9. [ ] Write unit tests

## Acceptance Criteria

- [ ] Report includes all required sections
- [ ] Citations are APA-formatted
- [ ] Manifest includes download commands
- [ ] Hash proof is deterministic
- [ ] Both JSON and Markdown outputs work
