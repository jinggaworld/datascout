"""Readiness score calculator — evaluates dataset quality across 5 dimensions."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from src.models.dataset import DatasetResult
from src.models.score import ReadinessScore, ScoreBreakdown

logger = logging.getLogger(__name__)


class ReadinessCalculator:
    """Calculate readiness scores (0-100) for datasets.

    Scores are computed from 5 weighted components:
    - Completeness (30%): low missing values, good profiling data
    - Freshness (20%): how recently the dataset was updated
    - Size (20%): number of rows (log scale)
    - Documentation (15%): description quality, tags, download availability
    - License clarity (15%): clear and permissive license
    """

    WEIGHTS = {
        "completeness": 0.30,
        "freshness": 0.20,
        "size": 0.20,
        "documentation": 0.15,
        "license": 0.15,
    }

    def calculate(self, dataset: DatasetResult) -> DatasetResult:
        """Calculate readiness score for a single dataset.

        Returns a copy with ``readiness_score`` populated.
        """
        breakdown = ScoreBreakdown(
            completeness=self._completeness_score(dataset),
            freshness=self._freshness_score(dataset),
            size=self._size_score(dataset),
            documentation=self._documentation_score(dataset),
            license=self._license_score(dataset),
        )

        # Weighted sum → 0-100 scale
        total = (
            breakdown.completeness * self.WEIGHTS["completeness"]
            + breakdown.freshness * self.WEIGHTS["freshness"]
            + breakdown.size * self.WEIGHTS["size"]
            + breakdown.documentation * self.WEIGHTS["documentation"]
            + breakdown.license * self.WEIGHTS["license"]
        )

        score = ReadinessScore(
            total=round(total * 100, 1),
            breakdown=breakdown,
        )

        return dataset.model_copy(update={"readiness_score": score})

    def calculate_batch(self, datasets: list[DatasetResult]) -> list[DatasetResult]:
        """Calculate readiness scores for a batch of datasets.

        Returns a new list sorted by descending readiness score.
        """
        scored = [self.calculate(d) for d in datasets]
        scored.sort(key=lambda d: d.readiness_score.total if d.readiness_score else 0, reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Scoring components (each returns 0.0 - 1.0)
    # ------------------------------------------------------------------

    def _completeness_score(self, d: DatasetResult) -> float:
        """Score based on data completeness (missing values).

        Uses profiling data if available, otherwise returns neutral 0.5.
        """
        if not d.preview:
            # No preview data → check if we at least have basic metadata
            has_rows = d.rows is not None and d.rows > 0
            has_cols = d.columns is not None and d.columns > 0
            if has_rows and has_cols:
                return 0.6  # Metadata available but no profile
            if has_rows or has_cols:
                return 0.5
            return 0.4  # No metadata at all

        # Check column-level completeness
        columns = d.preview.columns
        if not columns:
            return 0.5

        # Average null percentage across columns
        total_null_pct = 0.0
        for col in columns:
            total_null_pct += col.get("null_percentage", 0)
        avg_null_pct = total_null_pct / len(columns) if columns else 0

        # Lower null percentage → higher score
        return max(0.0, min(1.0, 1.0 - (avg_null_pct / 100)))

    def _freshness_score(self, d: DatasetResult) -> float:
        """Score based on how recently the dataset was updated.

        Linear decay over 2 years, floor at 0.1.
        """
        if not d.last_updated:
            return 0.5  # Unknown → neutral

        try:
            updated = datetime.fromisoformat(
                d.last_updated.replace("Z", "+00:00")
            )
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - updated).days
            return max(0.1, 1.0 - (days_ago / 730))  # 2 years
        except (ValueError, TypeError):
            return 0.5

    def _size_score(self, d: DatasetResult) -> float:
        """Score based on dataset size (log scale).

        10 rows → ~0.125, 1000 rows → 0.375, 1M rows → 0.75, 100M → 1.0
        """
        if not d.rows or d.rows <= 0:
            return 0.5  # Unknown → neutral

        return min(1.0, math.log10(max(d.rows, 1)) / 8)

    def _documentation_score(self, d: DatasetResult) -> float:
        """Score based on documentation quality.

        Checks description length, tag count, and download availability.
        """
        score = 0.3  # Base score

        # Description quality
        desc = d.description or ""
        if len(desc) > 200:
            score += 0.3
        elif len(desc) > 50:
            score += 0.15

        # Tags
        tags = d.tags or []
        if len(tags) >= 3:
            score += 0.2
        elif len(tags) >= 1:
            score += 0.1

        # Download availability
        if d.download_url:
            score += 0.15

        # File format specified
        if d.file_format:
            score += 0.05

        return min(1.0, score)

    def _license_score(self, d: DatasetResult) -> float:
        """Score based on license clarity and permissiveness.

        Commercial-ok licenses get highest score, research-only moderate,
        unknown licenses penalized.
        """
        from src.models.license import LicenseType

        ls = d.license_status
        if not ls or not ls.detected:
            if ls and ls.needs_verification:
                return 0.3  # Unknown → needs manual check
            return 0.4  # No license info at all

        if ls.license_type == LicenseType.COMMERCIAL_OK:
            return 1.0
        elif ls.license_type == LicenseType.RESEARCH_ONLY:
            return 0.6
        else:
            return 0.3
