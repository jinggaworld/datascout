from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LicenseType(str, Enum):
    """Classification of license types."""
    COMMERCIAL_OK = "commercial_ok"     # CC0, CC-BY, CC-BY-SA, MIT, Apache, ODbL, Unlicense
    RESEARCH_ONLY = "research_only"     # CC-BY-NC, CC-BY-NC-SA, CC-BY-ND, CC-BY-NC-ND
    UNKNOWN = "unknown"                 # No license, ambiguous, custom


class LicenseStatus(BaseModel):
    """Structured license status for a dataset."""
    detected: bool = Field(default=False, description="Whether a license was detected")
    license_type: LicenseType = Field(default=LicenseType.UNKNOWN, description="License classification")
    license_name: Optional[str] = Field(None, description="Specific license name (e.g., CC-BY-4.0)")
    needs_verification: bool = Field(default=False, description="Whether manual verification is needed")
    allows_commercial: Optional[bool] = Field(None, description="Whether commercial use is allowed")
    requires_attribution: Optional[bool] = Field(None, description="Whether attribution is required")
    source_text: Optional[str] = Field(None, description="Original license text from source")

    @property
    def is_clear(self) -> bool:
        """Check if license status is clear and actionable."""
        return self.detected and not self.needs_verification

    @property
    def is_commercial_friendly(self) -> bool:
        """Check if the license allows commercial use."""
        return self.license_type == LicenseType.COMMERCIAL_OK


# Known license patterns for regex matching
COMMERCIAL_OK_PATTERNS: dict[str, list[str]] = {
    "CC0": ["CC0", "Public Domain", "No Rights Reserved"],
    "CC-BY": ["CC-BY", "Creative Commons Attribution"],
    "CC-BY-SA": ["CC-BY-SA", "Attribution-ShareAlike"],
    "MIT": ["MIT License", "\bMIT\b"],
    "Apache": ["Apache 2.0", "Apache License"],
    "ODbL": ["ODbL", "Open Database License"],
    "Unlicense": ["Unlicense"],
}

RESEARCH_ONLY_PATTERNS: dict[str, list[str]] = {
    "CC-BY-NC": ["CC-BY-NC", "NonCommercial", "Non-Commercial"],
    "CC-BY-NC-SA": ["CC-BY-NC-SA"],
    "CC-BY-ND": ["CC-BY-ND", "NoDerivatives"],
    "CC-BY-NC-ND": ["CC-BY-NC-ND"],
}
