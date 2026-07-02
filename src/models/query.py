from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    SEARCH = "search"
    VERIFY = "verify"
    COMPARE = "compare"


class LicenseFilter(str, Enum):
    ANY = "any"
    COMMERCIAL_OK = "commercial_ok"
    RESEARCH_ONLY = "research_only"


class TimeRange(BaseModel):
    start: Optional[int] = Field(None, description="Tahun mulai")
    end: Optional[int] = Field(None, description="Tahun selesai")


class ParsedQuery(BaseModel):
    topic: str = Field(..., description="Topik utama dataset")
    keywords: list[str] = Field(default_factory=list, description="Kata kunci terkait")
    region: Optional[str] = Field(None, description="Wilayah: country code atau global")
    time_range: Optional[TimeRange] = None
    min_rows: Optional[int] = Field(None, description="Minimum jumlah baris")
    format: list[str] = Field(default_factory=list, description="Format: csv, json, parquet")
    license: LicenseFilter = LicenseFilter.ANY
    domain: str = Field(..., description="Domain: finance, health, climate, dll")
    intent: IntentType = IntentType.SEARCH
    verify_url: Optional[str] = Field(None, description="URL untuk mode verifikasi")
    model_used: str = Field(default="", description="Model Groq yang dipakai")
    parsing_time_ms: int = Field(default=0, description="Waktu parsing dalam ms")
