from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery


class Citation(BaseModel):
    dataset_id: str
    apa: str = Field(description="APA format citation")
    bibtex: str = Field(default="", description="BibTeX format citation")


class ManifestEntry(BaseModel):
    dataset_id: str
    title: str
    source: str
    download_url: Optional[str] = None
    source_url: str
    file_format: Optional[str] = None
    checksum_algorithm: str = "sha256"
    download_command: str = ""


class Manifest(BaseModel):
    version: str = "1.0"
    generator: str = "DataScout"
    datasets: list[ManifestEntry] = Field(default_factory=list)
    manifest_hash: str = ""


class DatasetComparison(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class FinalReport(BaseModel):
    query: ParsedQuery
    timestamp: str = ""
    total_sources_searched: int = 0
    total_results_found: int = 0
    deduped_results: int = 0
    top_datasets: list[DatasetResult] = Field(default_factory=list)
    comparison_table: Optional[DatasetComparison] = None
    summary: str = ""
    domain_distribution: dict[str, int] = Field(default_factory=dict)
    source_distribution: dict[str, int] = Field(default_factory=dict)
    citations: list[Citation] = Field(default_factory=list)
    manifest: Manifest = Field(default_factory=Manifest)
    hash_proof: str = ""
