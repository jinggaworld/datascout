"""Unit tests for readiness score calculator engine."""

from __future__ import annotations

import pandas as pd

from src.engine.score import ReadinessCalculator
from src.engine.license import LicenseExtractor
from src.engine.profiler import DataProfiler
from src.models.dataset import DatasetResult, DataPreview
from src.models.license import LicenseStatus, LicenseType
from src.models.score import ReadinessScore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ds(
    title: str = "Test Dataset",
    description: str = "A test dataset for scoring",
    source: str = "huggingface",
    rows: int | None = 1000,
    columns: int | None = 10,
    tags: list[str] | None = None,
    last_updated: str | None = "2024-01-15",
    download_url: str | None = "https://example.com/download",
    file_format: str | None = "csv",
    preview: DataPreview | None = None,
    license_status: LicenseStatus | None = None,
    **kwargs,
) -> DatasetResult:
    return DatasetResult(
        id=f"{source}-1",
        title=title,
        description=description,
        source=source,
        source_url=f"https://example.com/{source}/1",
        rows=rows,
        columns=columns,
        tags=tags or [],
        last_updated=last_updated,
        download_url=download_url,
        file_format=file_format,
        preview=preview,
        license_status=license_status or LicenseStatus(),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# ReadinessCalculator tests
# ---------------------------------------------------------------------------


class TestReadinessCalculator:
    def setup_method(self):
        self.calc = ReadinessCalculator()

    def test_calculate_returns_readiness_score(self):
        ds = _ds()
        result = self.calc.calculate(ds)
        assert result.readiness_score is not None
        assert isinstance(result.readiness_score, ReadinessScore)

    def test_score_range(self):
        """Score should be between 0 and 100."""
        ds = _ds()
        result = self.calc.calculate(ds)
        assert 0 <= result.readiness_score.total <= 100

    def test_breakdown_has_all_components(self):
        ds = _ds()
        result = self.calc.calculate(ds)
        b = result.readiness_score.breakdown
        assert 0 <= b.completeness <= 1
        assert 0 <= b.freshness <= 1
        assert 0 <= b.size <= 1
        assert 0 <= b.documentation <= 1
        assert 0 <= b.license <= 1

    def test_grade_auto_computed(self):
        """Grade should be auto-computed by model validator."""
        ds = _ds()
        result = self.calc.calculate(ds)
        score = result.readiness_score.total
        grade = result.readiness_score.grade
        if score >= 80:
            assert grade == "A"
        elif score >= 60:
            assert grade == "B"
        elif score >= 40:
            assert grade == "C"
        elif score >= 20:
            assert grade == "D"
        else:
            assert grade == "F"

    def test_high_quality_dataset(self):
        """Well-documented, large, fresh, licensed dataset should score high."""
        ds = _ds(
            description="A comprehensive dataset with detailed documentation about climate patterns worldwide with extensive metadata",
            rows=1000000,
            tags=["climate", "weather", "temperature", "environment"],
            last_updated="2025-06-01",
            license_status=LicenseStatus(
                detected=True,
                license_type=LicenseType.COMMERCIAL_OK,
                license_name="CC-BY",
            ),
        )
        result = self.calc.calculate(ds)
        assert result.readiness_score.total >= 60  # Should be B or better

    def test_low_quality_dataset(self):
        """Sparse, old, unlicensed dataset should score low."""
        ds = _ds(
            description="data",
            rows=10,
            tags=[],
            last_updated="2020-01-01",
            download_url=None,
            file_format=None,
            license_status=LicenseStatus(detected=False),
        )
        result = self.calc.calculate(ds)
        assert result.readiness_score.total < 50

    def test_unknown_metadata_neutral(self):
        """Dataset with no metadata should get neutral scores."""
        ds = _ds(rows=None, columns=None, last_updated=None, tags=[])
        result = self.calc.calculate(ds)
        # Should still produce a valid score
        assert 0 <= result.readiness_score.total <= 100

    def test_completeness_with_preview(self):
        """Preview with low null percentage should boost completeness."""
        preview = DataPreview(
            columns=[
                {"name": "a", "null_percentage": 0.0},
                {"name": "b", "null_percentage": 5.0},
            ],
            sample_rows=[],
            total_rows=1000,
            total_columns=2,
        )
        ds = _ds(preview=preview)
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.completeness >= 0.9

    def test_completeness_with_high_nulls(self):
        """Preview with high null percentage should lower completeness."""
        preview = DataPreview(
            columns=[
                {"name": "a", "null_percentage": 50.0},
                {"name": "b", "null_percentage": 80.0},
            ],
            sample_rows=[],
            total_rows=1000,
            total_columns=2,
        )
        ds = _ds(preview=preview)
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.completeness <= 0.5

    def test_license_scores(self):
        """Different license types should produce different scores."""
        # Commercial OK
        ds_commercial = _ds(license_status=LicenseStatus(
            detected=True, license_type=LicenseType.COMMERCIAL_OK, license_name="MIT"
        ))
        result_c = self.calc.calculate(ds_commercial)
        assert result_c.readiness_score.breakdown.license == 1.0

        # Research only
        ds_research = _ds(license_status=LicenseStatus(
            detected=True, license_type=LicenseType.RESEARCH_ONLY, license_name="CC-BY-NC"
        ))
        result_r = self.calc.calculate(ds_research)
        assert result_r.readiness_score.breakdown.license == 0.6

        # Unknown
        ds_unknown = _ds(license_status=LicenseStatus(
            detected=False, license_type=LicenseType.UNKNOWN, needs_verification=True
        ))
        result_u = self.calc.calculate(ds_unknown)
        assert result_u.readiness_score.breakdown.license == 0.3

    def test_freshness_recent(self):
        """Recently updated dataset should have high freshness."""
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        ds = _ds(last_updated=recent)
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.freshness >= 0.8

    def test_freshness_old(self):
        """Old dataset should have low freshness."""
        ds = _ds(last_updated="2020-01-01")
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.freshness <= 0.4

    def test_freshness_unknown(self):
        """Unknown last_updated should get neutral freshness."""
        ds = _ds(last_updated=None)
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.freshness == 0.5

    def test_size_large(self):
        """Large dataset should have high size score."""
        ds = _ds(rows=10000000)  # 10M rows
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.size >= 0.8

    def test_size_small(self):
        """Small dataset should have low size score."""
        ds = _ds(rows=10)
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.size <= 0.2

    def test_size_unknown(self):
        """Unknown size should get neutral score."""
        ds = _ds(rows=None)
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.size == 0.5

    def test_documentation_good(self):
        """Well-documented dataset should have high doc score."""
        ds = _ds(
            description="A comprehensive dataset with detailed documentation about climate patterns worldwide including extensive metadata and usage guidelines",
            tags=["climate", "weather", "temperature"],
            download_url="https://example.com/download",
            file_format="csv",
        )
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.documentation >= 0.8

    def test_documentation_poor(self):
        """Poorly documented dataset should have low doc score."""
        ds = _ds(description="data", tags=[], download_url=None, file_format=None)
        result = self.calc.calculate(ds)
        assert result.readiness_score.breakdown.documentation <= 0.4

    def test_calculate_batch(self):
        """Batch calculation should return all scored and sorted."""
        datasets = [
            _ds(title="Small", rows=10),
            _ds(title="Large", rows=1000000),
            _ds(title="Medium", rows=1000),
        ]
        results = self.calc.calculate_batch(datasets)
        assert len(results) == 3
        # Should be sorted by score descending
        scores = [r.readiness_score.total for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_calculate_batch_empty(self):
        assert self.calc.calculate_batch([]) == []

    def test_original_not_mutated(self):
        """Original dataset should not be mutated."""
        ds = _ds()
        result = self.calc.calculate(ds)
        assert ds.readiness_score is None
        assert result.readiness_score is not None

    def test_score_is_deterministic(self):
        """Same dataset should always get the same score."""
        ds = _ds()
        r1 = self.calc.calculate(ds)
        r2 = self.calc.calculate(ds)
        assert r1.readiness_score.total == r2.readiness_score.total

    def test_weights_sum_to_one(self):
        total = sum(ReadinessCalculator.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001
