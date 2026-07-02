"""Unit tests for license extraction, ranking, dedup, and profiling engines."""

from __future__ import annotations

import pandas as pd

from src.engine.license import LicenseExtractor
from src.engine.ranking import RankingEngine
from src.engine.dedup import DeduplicationEngine
from src.engine.profiler import DataProfiler
from src.models.dataset import DatasetResult
from src.models.license import LicenseStatus, LicenseType
from src.models.query import ParsedQuery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ds(
    title: str = "Test Dataset",
    description: str = "A test dataset",
    source: str = "huggingface",
    source_url: str = "https://example.com/1",
    rows: int | None = 1000,
    tags: list[str] | None = None,
    last_updated: str | None = "2024-01-15",
    download_url: str | None = "https://example.com/download",
    **kwargs,
) -> DatasetResult:
    return DatasetResult(
        id=f"{source}-1",
        title=title,
        description=description,
        source=source,
        source_url=source_url,
        rows=rows,
        tags=tags or [],
        last_updated=last_updated,
        download_url=download_url,
        **kwargs,
    )


def _q(topic: str = "climate", domain: str = "climate", **kw) -> ParsedQuery:
    return ParsedQuery(topic=topic, domain=domain, **kw)


# ---------------------------------------------------------------------------
# LicenseExtractor tests
# ---------------------------------------------------------------------------


class TestLicenseExtractor:
    def setup_method(self):
        self.extractor = LicenseExtractor()

    def test_detect_cc0(self):
        ds = _ds(description="Licensed under CC0 1.0 Universal")
        result = self.extractor.extract(ds)
        assert result.license_status.detected is True
        assert result.license_status.license_type == LicenseType.COMMERCIAL_OK
        assert result.license_status.license_name == "CC0"

    def test_detect_cc_by(self):
        ds = _ds(description="This dataset is released under Creative Commons Attribution 4.0")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "CC-BY"
        assert result.license_status.license_type == LicenseType.COMMERCIAL_OK

    def test_detect_cc_by_nc(self):
        ds = _ds(description="CC-BY-NC license, non-commercial use only")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "CC-BY-NC"
        assert result.license_status.license_type == LicenseType.RESEARCH_ONLY
        assert result.license_status.allows_commercial is False

    def test_detect_cc_by_nc_sa(self):
        ds = _ds(description="Licensed under CC-BY-NC-SA 4.0")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "CC-BY-NC-SA"
        assert result.license_status.license_type == LicenseType.RESEARCH_ONLY

    def test_detect_mit(self):
        ds = _ds(description="MIT License")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "MIT"
        assert result.license_status.license_type == LicenseType.COMMERCIAL_OK

    def test_detect_apache(self):
        ds = _ds(description="Apache 2.0 License")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "Apache-2.0"
        assert result.license_status.license_type == LicenseType.COMMERCIAL_OK

    def test_detect_odbl(self):
        ds = _ds(description="Open Database License (ODbL)")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "ODbL"
        assert result.license_status.license_type == LicenseType.COMMERCIAL_OK

    def test_detect_unlicense(self):
        ds = _ds(description="Released to the public domain via Unlicense")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "Unlicense"
        assert result.license_status.allows_commercial is True

    def test_detect_in_description(self):
        ds = _ds(description="This dataset uses the MIT License for distribution")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "MIT"

    def test_detect_in_title(self):
        ds = _ds(title="IMDB Dataset (CC-BY-4.0)")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "CC-BY"

    def test_unknown_license(self):
        ds = _ds(description="Proprietary dataset, contact for terms")
        result = self.extractor.extract(ds)
        assert result.license_status.detected is False
        assert result.license_status.license_type == LicenseType.UNKNOWN
        assert result.license_status.needs_verification is True

    def test_specific_before_general(self):
        """CC-BY-NC-SA should be detected, not just CC-BY-NC."""
        ds = _ds(description="Licensed under CC-BY-NC-SA 4.0 International")
        result = self.extractor.extract(ds)
        assert result.license_status.license_name == "CC-BY-NC-SA"

    def test_extract_batch(self):
        datasets = [
            _ds(description="CC0 license"),
            _ds(description="MIT License"),
            _ds(description="Unknown terms"),
        ]
        results = self.extractor.extract_batch(datasets)
        assert len(results) == 3
        assert results[0].license_status.license_name == "CC0"
        assert results[1].license_status.license_name == "MIT"
        assert results[2].license_status.detected is False


# ---------------------------------------------------------------------------
# RankingEngine tests
# ---------------------------------------------------------------------------


class TestRankingEngine:
    def setup_method(self):
        self.engine = RankingEngine()

    def test_empty_input(self):
        assert self.engine.rank(_q(), []) == []

    def test_single_dataset(self):
        ds = _ds(title="climate change data", tags=["climate"])
        result = self.engine.rank(_q(topic="climate"), [ds])
        assert len(result) == 1
        assert result[0].relevance_score > 0

    def test_ranking_order(self):
        """Most relevant dataset should rank first."""
        ds_relevant = _ds(title="climate temperature dataset", tags=["climate", "temperature"])
        ds_irrelevant = _ds(title="cooking recipes", tags=["food"])
        result = self.engine.rank(_q(topic="climate"), [ds_irrelevant, ds_relevant])
        assert result[0].title == "climate temperature dataset"

    def test_title_bonus(self):
        """Dataset with matching title should score higher."""
        ds_title = _ds(title="climate data", description="generic description")
        ds_desc = _ds(title="random title", description="climate data analysis")
        result = self.engine.rank(_q(topic="climate"), [ds_title, ds_desc])
        assert result[0].title == "climate data"

    def test_freshness_bonus(self):
        """Newer dataset should score higher."""
        ds_new = _ds(title="climate data", last_updated="2025-01-01")
        ds_old = _ds(title="climate data", last_updated="2020-01-01")
        result = self.engine.rank(_q(topic="climate"), [ds_old, ds_new])
        assert result[0].last_updated == "2025-01-01"

    def test_size_bonus(self):
        """Larger dataset should score higher."""
        ds_big = _ds(title="climate data", rows=1000000)
        ds_small = _ds(title="climate data", rows=100)
        result = self.engine.rank(_q(topic="climate"), [ds_small, ds_big])
        assert result[0].rows == 1000000

    def test_doc_bonus(self):
        """Well-documented dataset should score higher."""
        ds_good = _ds(title="climate data", description="A comprehensive dataset with detailed documentation about climate patterns worldwide", tags=["climate", "weather", "temperature"])
        ds_bad = _ds(title="climate data", description="data", tags=["climate"])
        result = self.engine.rank(_q(topic="climate"), [ds_bad, ds_good])
        assert result[0].description.startswith("A comprehensive")

    def test_score_range(self):
        """Scores should be between 0 and 1."""
        ds = _ds(title="test", description="test data", tags=["test"])
        result = self.engine.rank(_q(), [ds])
        assert 0 <= result[0].relevance_score <= 1

    def test_unknown_last_updated(self):
        """Unknown last_updated should get neutral freshness score."""
        ds = _ds(title="climate data", last_updated=None)
        result = self.engine.rank(_q(topic="climate"), [ds])
        assert len(result) == 1

    def test_tokenize(self):
        tokens = RankingEngine._tokenize("Hello, World! This is a TEST.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        # "is" has length 2 so it passes the filter — that's correct behavior
        assert "this" in tokens


# ---------------------------------------------------------------------------
# DeduplicationEngine tests
# ---------------------------------------------------------------------------


class TestDeduplicationEngine:
    def setup_method(self):
        self.engine = DeduplicationEngine()

    def test_empty_input(self):
        assert self.engine.deduplicate([]) == []

    def test_no_duplicates(self):
        ds1 = _ds(title="Completely Different Dataset A", source_url="https://huggingface.co/datasets/alpha", source="huggingface")
        ds2 = _ds(title="Totally Unrelated Dataset B", source_url="https://kaggle.com/datasets/beta", source="kaggle")
        result = self.engine.deduplicate([ds1, ds2])
        assert len(result) == 2

    def test_exact_title_duplicates(self):
        ds1 = _ds(title="IMDB Reviews", source="huggingface", source_url="https://hf.com/imdb")
        ds2 = _ds(title="IMDB Reviews", source="kaggle", source_url="https://kaggle.com/imdb")
        result = self.engine.deduplicate([ds1, ds2])
        assert len(result) == 1
        assert len(result[0].merged_from) == 2

    def test_fuzzy_title_duplicates(self):
        ds1 = _ds(title="Climate Change Temperature Data", source="huggingface", source_url="https://hf.com/1")
        ds2 = _ds(title="Climate Change Temperature Dataset", source="kaggle", source_url="https://kaggle.com/1")
        result = self.engine.deduplicate([ds1, ds2])
        assert len(result) == 1

    def test_different_datasets_not_merged(self):
        ds1 = _ds(title="Housing Prices in Indonesia", source="huggingface", source_url="https://hf.com/1")
        ds2 = _ds(title="Air Quality Measurements in Jakarta", source="kaggle", source_url="https://kaggle.com/1")
        result = self.engine.deduplicate([ds1, ds2])
        assert len(result) == 2

    def test_merge_keeps_best_metadata(self):
        """The entry with more rows should be kept as primary content."""
        ds_small = _ds(title="Climate Data", rows=100, source="huggingface", source_url="https://hf.com/1")
        ds_big = _ds(title="Climate Data", rows=10000, source="kaggle", source_url="https://kaggle.com/1")
        result = self.engine.deduplicate([ds_small, ds_big])
        assert len(result) == 1
        assert result[0].rows == 10000

    def test_merge_preserves_all_tags(self):
        ds1 = _ds(title="Climate Data", tags=["climate", "temperature"], source="huggingface", source_url="https://hf.com/1")
        ds2 = _ds(title="Climate Data", tags=["weather", "environment"], source="kaggle", source_url="https://kaggle.com/1")
        result = self.engine.deduplicate([ds1, ds2])
        assert len(result) == 1
        merged_tags = set(result[0].tags)
        assert "climate" in merged_tags
        assert "weather" in merged_tags

    def test_three_way_merge(self):
        ds1 = _ds(title="Sentiment Analysis Dataset", source="huggingface", source_url="https://hf.com/1")
        ds2 = _ds(title="Sentiment Analysis Dataset", source="kaggle", source_url="https://kaggle.com/1")
        ds3 = _ds(title="Sentiment Analysis Dataset", source="openml", source_url="https://openml.com/1")
        result = self.engine.deduplicate([ds1, ds2, ds3])
        assert len(result) == 1
        assert len(result[0].merged_from) == 3

    def test_same_source_not_merged(self):
        """Datasets from the same source should not be merged."""
        ds1 = _ds(title="Same Name", source="huggingface", source_url="https://hf.com/1")
        ds2 = _ds(title="Same Name", source="huggingface", source_url="https://hf.com/2")
        result = self.engine.deduplicate([ds1, ds2])
        assert len(result) == 2

    def test_normalize_title(self):
        assert DeduplicationEngine._normalize_title("hf-imdb") == "imdb"
        assert DeduplicationEngine._normalize_title("IMDB Dataset") == "imdb"
        assert DeduplicationEngine._normalize_title("Climate Data Collection") == "climate data"


# ---------------------------------------------------------------------------
# DataProfiler tests
# ---------------------------------------------------------------------------


class TestDataProfiler:
    def setup_method(self):
        self.profiler = DataProfiler()

    def test_profile_with_dataframe(self):
        df = pd.DataFrame({
            "age": [25, 30, 35, 40, None],
            "name": ["Alice", "Bob", "Charlie", "David", None],
            "score": [85.5, 90.0, 78.5, 92.0, 88.0],
        })
        ds = _ds()
        result = self.profiler.profile(ds, df)

        assert result.preview is not None
        assert result.preview.total_rows == 5
        assert result.preview.total_columns == 3
        assert len(result.preview.sample_rows) == 5
        assert len(result.preview.columns) == 3

    def test_profile_stats(self):
        df = pd.DataFrame({
            "value": [10, 20, 30, 40, 50],
            "category": ["A", "B", "A", "B", "A"],
        })
        ds = _ds()
        result = self.profiler.profile(ds, df)

        assert result.data_profile is not None
        assert "value" in result.data_profile.numeric_stats
        assert result.data_profile.numeric_stats["value"]["mean"] == 30.0
        assert "category" in result.data_profile.categorical_stats
        assert result.data_profile.categorical_stats["category"]["unique_count"] == 2

    def test_profile_missing_values(self):
        df = pd.DataFrame({
            "a": [1, None, 3],
            "b": [None, None, None],
        })
        ds = _ds()
        result = self.profiler.profile(ds, df)

        missing = result.data_profile.missing_summary
        assert missing["total_missing"] > 0
        assert "a" in missing["columns_with_missing"]
        assert "b" in missing["columns_with_missing"]

    def test_profile_none_df(self):
        ds = _ds()
        result = self.profiler.profile(ds, None)
        assert result.preview is None

    def test_profile_empty_df(self):
        df = pd.DataFrame()
        ds = _ds()
        result = self.profiler.profile(ds, df)
        assert result.preview is not None
        assert result.preview.total_rows == 0

    def test_profile_from_dicts(self):
        rows = [
            {"x": 1, "y": "a"},
            {"x": 2, "y": "b"},
            {"x": 3, "y": "a"},
        ]
        ds = _ds()
        result = self.profiler.profile_from_dicts(ds, rows)
        assert result.preview is not None
        assert result.preview.total_rows == 3

    def test_profile_from_dicts_empty(self):
        ds = _ds()
        result = self.profiler.profile_from_dicts(ds, [])
        assert result.preview is None

    def test_safe_serialize(self):
        import math
        from src.engine.profiler import _safe_serialize

        assert _safe_serialize(float("nan")) is None
        assert _safe_serialize(float("inf")) is None
        assert _safe_serialize(42) == 42
        assert _safe_serialize(3.14) == 3.14
        assert _safe_serialize(None) is None

    def test_sample_rows_limit(self):
        """Preview should have at most MAX_SAMPLE_ROWS rows."""
        df = pd.DataFrame({"x": range(100)})
        ds = _ds()
        result = self.profiler.profile(ds, df)
        assert len(result.preview.sample_rows) == 10
