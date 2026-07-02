from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from src.models.license import LicenseStatus
from src.models.score import ReadinessScore


class DataPreview(BaseModel):
    """Preview data (sample rows, schema)."""
    columns: list[dict[str, Any]] = Field(default_factory=list, description="Column definitions")
    sample_rows: list[dict[str, Any]] = Field(default_factory=list, description="Sample data rows")
    total_rows: int = Field(default=0, description="Total number of rows")
    total_columns: int = Field(default=0, description="Total number of columns")


class DataProfile(BaseModel):
    """Statistical profile of dataset."""
    numeric_stats: dict[str, Any] = Field(default_factory=dict, description="Numeric column statistics")
    categorical_stats: dict[str, Any] = Field(default_factory=dict, description="Categorical column statistics")
    missing_summary: dict[str, Any] = Field(default_factory=dict, description="Missing value analysis")


class DatasetResult(BaseModel):
    """A single dataset result from a data source search."""

    id: str = Field(..., description="Unique dataset identifier")
    title: str = Field(..., description="Dataset title")
    description: str = Field(default="", description="Dataset description")
    source: str = Field(..., description="Source name: huggingface, kaggle, etc.")
    source_url: str = Field(..., description="URL at the original source")
    download_url: Optional[str] = Field(None, description="Direct download link")

    # Metadata
    rows: Optional[int] = Field(None, description="Number of data rows")
    columns: Optional[int] = Field(None, description="Number of columns")
    file_size_mb: Optional[float] = Field(None, description="File size in MB")
    file_format: Optional[str] = Field(None, description="File format: csv, json, parquet")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")

    # Scores
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance score (0-1)")
    readiness_score: Optional[ReadinessScore] = Field(None, description="Readiness score (0-100)")

    # License
    license_status: LicenseStatus = Field(default_factory=LicenseStatus, description="License status")

    # Preview
    preview: Optional[DataPreview] = Field(None, description="Data preview (sample rows, schema)")

    # Tags & Domain
    tags: list[str] = Field(default_factory=list, description="Dataset tags")
    domain: str = Field(default="other", description="Domain category")
    region: Optional[str] = Field(None, description="Geographic region")

    # Dedup
    merged_from: list[str] = Field(default_factory=list, description="Source IDs if merged from duplicates")
