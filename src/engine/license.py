"""License extraction & classification engine — detects license from dataset metadata."""

from __future__ import annotations

import logging
import re

from src.models.dataset import DatasetResult
from src.models.license import LicenseStatus, LicenseType

logger = logging.getLogger(__name__)


class LicenseExtractor:
    """Extract and classify dataset licenses from metadata text.

    Uses regex pattern matching against known license phrases.
    Handles Creative Commons, MIT, Apache, ODbL, and other common licenses.
    """

    # ------------------------------------------------------------------
    # License patterns: name → list of regex patterns
    # ------------------------------------------------------------------

    PATTERNS: dict[str, list[str]] = {
        "CC0": [r"\bCC0\b", r"\bPublic\s+Domain\b", r"\bNo\s+Rights\s+Reserved\b"],
        "CC-BY": [r"\bCC-BY\b(?![-](?:NC|SA|ND|NC-SA|NC-ND)\b)", r"Creative Commons Attribution\b(?![-](?:NC|SA|ND|NC-SA|NC-ND)\b)"],
        "CC-BY-SA": [r"\bCC-BY-SA\b", r"Attribution-ShareAlike"],
        "CC-BY-NC": [r"\bCC-BY-NC\b(?![-]\w)", r"\bNonCommercial\b", r"\bNon-Commercial\b"],
        "CC-BY-NC-SA": [r"\bCC-BY-NC-SA\b"],
        "CC-BY-ND": [r"\bCC-BY-ND\b(?![-]\w)", r"\bNoDerivatives\b"],
        "CC-BY-NC-ND": [r"\bCC-BY-NC-ND\b"],
        "MIT": [r"\bMIT\b\s*[Ll]icense", r"\bmit\b(?![-\w])"],
        "Apache-2.0": [r"Apache\s*2\.0", r"Apache\s*License\s*2"],
        "ODbL": [r"\bODbL\b", r"Open\s*Database\s*License"],
        "Unlicense": [r"\bUnlicense\b"],
        "GPL-3.0": [r"\bGPL[- ]v?3\b", r"GNU\s*General\s*Public\s*License.*3"],
        "BSD-3-Clause": [r"\bBSD[- ]3[- ]Clause\b"],
        "ISC": [r"\bISC\b\s*License"],
    }

    COMMERCIAL_OK = frozenset({
        "CC0", "CC-BY", "CC-BY-SA", "MIT", "Apache-2.0",
        "ODbL", "Unlicense", "GPL-3.0", "BSD-3-Clause", "ISC",
    })

    RESEARCH_ONLY = frozenset({
        "CC-BY-NC", "CC-BY-NC-SA", "CC-BY-ND", "CC-BY-NC-ND",
    })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, dataset: DatasetResult) -> DatasetResult:
        """Extract and classify license from dataset metadata.

        Searches description, title, tags, and source URL for known
        license patterns. Returns a copy of the dataset with the
        ``license_status`` field populated.
        """
        text = self._build_search_text(dataset)
        detected = self._detect_license(text)

        if detected in self.COMMERCIAL_OK:
            status = LicenseStatus(
                detected=True,
                license_type=LicenseType.COMMERCIAL_OK,
                license_name=detected,
                needs_verification=False,
                allows_commercial=True,
                requires_attribution=detected not in {"CC0", "Unlicense"},
                source_text=text[:200],
            )
        elif detected in self.RESEARCH_ONLY:
            status = LicenseStatus(
                detected=True,
                license_type=LicenseType.RESEARCH_ONLY,
                license_name=detected,
                needs_verification=False,
                allows_commercial=False,
                requires_attribution=True,
                source_text=text[:200],
            )
        else:
            status = LicenseStatus(
                detected=False,
                license_type=LicenseType.UNKNOWN,
                license_name=None,
                needs_verification=True,
                source_text=text[:200] if text else None,
            )

        return dataset.model_copy(update={"license_status": status})

    def extract_batch(self, datasets: list[DatasetResult]) -> list[DatasetResult]:
        """Extract licenses for a batch of datasets."""
        return [self.extract(d) for d in datasets]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_search_text(self, dataset: DatasetResult) -> str:
        """Combine all text fields for pattern matching."""
        parts = [
            dataset.title or "",
            dataset.description or "",
            dataset.source_url or "",
        ]
        tags = dataset.tags or []
        parts.extend(tags)
        return " ".join(str(p) for p in parts if p)

    def _detect_license(self, text: str) -> str | None:
        """Detect license name from text using regex patterns.

        Checks in a specific order to prefer more specific licenses
        (e.g., CC-BY-NC-SA before CC-BY-NC).
        """
        # Order matters: check specific licenses before general ones
        check_order = [
            "CC-BY-NC-ND", "CC-BY-NC-SA", "CC-BY-NC", "CC-BY-ND",
            "CC-BY-SA", "CC-BY",
            "Unlicense",
            "CC0",
            "Apache-2.0", "MIT", "GPL-3.0", "BSD-3-Clause", "ISC",
            "ODbL",
        ]

        for license_name in check_order:
            patterns = self.PATTERNS.get(license_name, [])
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return license_name

        return None
