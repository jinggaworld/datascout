from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class LicenseStatus(BaseModel):
    detected: bool = False
    license_type: str = "unknown"
    license_name: Optional[str] = None
    needs_verification: bool = False


class DataPreview(BaseModel):
    columns: list[dict[str, Any]] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    total_rows: int = 0
    total_columns: int = 0


class DataProfile(BaseModel):
    numeric_stats: dict[str, Any] = Field(default_factory=dict)
    categorical_stats: dict[str, Any] = Field(default_factory=dict)
    missing_summary: dict[str, Any] = Field(default_factory=dict)


class ReadinessScore(BaseModel):
    total: float = 0.0
    grade: str = "F"
    breakdown: dict[str, float] = Field(default_factory=dict)


class DatasetResult(BaseModel):
    id: str
    title: str
    description: str = ""
    source: str
    source_url: str
    download_url: Optional[str] = None
    rows: Optional[int] = None
    columns: Optional[int] = None
    file_size_mb: Optional[float] = None
    file_format: Optional[str] = None
    last_updated: Optional[str] = None
    relevance_score: float = 0.0
    readiness_score: Optional[ReadinessScore] = None
    license_status: LicenseStatus = Field(default_factory=LicenseStatus)
    preview: Optional[DataPreview] = None
    tags: list[str] = Field(default_factory=list)
    domain: str = "other"
    region: Optional[str] = None
    merged_from: list[str] = Field(default_factory=list)
