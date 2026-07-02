"""DataScout data models — Pydantic schemas for the entire pipeline."""

from src.models.cap import (
    CapDelivery,
    CapNegotiation,
    CapOrder,
    CapOrderStatus,
    CapSettlement,
)
from src.models.dataset import DataPreview, DataProfile, DatasetResult
from src.models.license import LicenseStatus, LicenseType
from src.models.query import IntentType, LicenseFilter, ParsedQuery, TimeRange
from src.models.report import Citation, DatasetComparison, FinalReport, Manifest, ManifestEntry
from src.models.score import ReadinessScore, RelevanceScore, ScoreBreakdown

__all__ = [
    # Query
    "ParsedQuery",
    "TimeRange",
    "IntentType",
    "LicenseFilter",
    # Dataset
    "DatasetResult",
    "DataPreview",
    "DataProfile",
    # Score
    "ReadinessScore",
    "ScoreBreakdown",
    "RelevanceScore",
    # License
    "LicenseStatus",
    "LicenseType",
    # Report
    "FinalReport",
    "Citation",
    "Manifest",
    "ManifestEntry",
    "DatasetComparison",
    # CAP
    "CapOrder",
    "CapOrderStatus",
    "CapDelivery",
    "CapSettlement",
    "CapNegotiation",
]
