"""Unit tests for report generator, citations, and manifest modules."""

from __future__ import annotations

from src.report.citations import CitationFormatter
from src.report.manifest import ManifestBuilder
from src.report.generator import ReportGenerator, generate_markdown
from src.models.dataset import DatasetResult
from src.models.license import LicenseStatus, LicenseType
from src.models.query import ParsedQuery
from src.models.score import ReadinessScore, ScoreBreakdown


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ds(
    title: str = "test-dataset",
    source: str = "huggingface",
    rows: int = 1000,
    tags: list[str] | None = None,
    last_updated: str | None = "2024-01-15",
    download_url: str | None = "https://example.com/download",
    file_format: str | None = "csv",
    score_total: float = 70.0,
    **kwargs,
) -> DatasetResult:
    return DatasetResult(
        id=f"{source}-1",
        title=title,
        description="A comprehensive test dataset for evaluation purposes",
        source=source,
        source_url=f"https://{source}.com/{title}",
        rows=rows,
        tags=tags or ["test"],
        last_updated=last_updated,
        download_url=download_url,
        file_format=file_format,
        readiness_score=ReadinessScore(
            total=score_total,
            breakdown=ScoreBreakdown(completeness=0.7, freshness=0.8, size=0.6, documentation=0.7, license=0.9),
        ),
        license_status=LicenseStatus(detected=True, license_type=LicenseType.COMMERCIAL_OK, license_name="MIT"),
        **kwargs,
    )


def _q(topic: str = "climate", domain: str = "climate", **kw) -> ParsedQuery:
    return ParsedQuery(topic=topic, domain=domain, **kw)


# ---------------------------------------------------------------------------
# CitationFormatter tests
# ---------------------------------------------------------------------------


class TestCitationFormatter:
    def setup_method(self):
        self.formatter = CitationFormatter()

    def test_format_citation(self):
        ds = _ds(title="org/climate-data", source="huggingface")
        citation = self.formatter.format_citation(ds)
        assert citation.dataset_id == ds.id
        assert "org" in citation.apa
        assert "Hugging Face" in citation.apa
        assert ds.source_url in citation.apa
        assert "climate-data" in citation.apa

    def test_apa_format(self):
        ds = _ds(title="my-dataset", source="kaggle")
        citation = self.formatter.format_citation(ds)
        # APA: Author. (Year). Title. Source. URL
        assert citation.apa.startswith("Kaggle.")
        assert "my-dataset" in citation.apa

    def test_bibtex_format(self):
        ds = _ds(title="test", source="openml")
        citation = self.formatter.format_citation(ds)
        assert "@misc{" in citation.bibtex
        assert "author =" in citation.bibtex
        assert "year =" in citation.bibtex
        assert "url =" in citation.bibtex

    def test_format_batch(self):
        datasets = [_ds(title=f"ds-{i}") for i in range(3)]
        citations = self.formatter.format_batch(datasets)
        assert len(citations) == 3
        for c in citations:
            assert c.apa != ""

    def test_author_from_title(self):
        ds = _ds(title="stanford/awesome-dataset")
        citation = self.formatter.format_citation(ds)
        assert "stanford" in citation.apa

    def test_author_fallback(self):
        ds = _ds(title="my-dataset", source="kaggle")
        citation = self.formatter.format_citation(ds)
        assert "Kaggle" in citation.apa  # Falls back to source name

    def test_year_from_last_updated(self):
        ds = _ds(last_updated="2023-06-15T10:00:00Z")
        citation = self.formatter.format_citation(ds)
        assert "2023" in citation.apa

    def test_source_names(self):
        for source, expected in [
            ("huggingface", "Hugging Face"),
            ("kaggle", "Kaggle"),
            ("openml", "OpenML"),
            ("data_gov", "data.gov"),
            ("worldbank", "World Bank"),
        ]:
            ds = _ds(source=source)
            name = self.formatter._get_source_name(ds)
            assert name == expected


# ---------------------------------------------------------------------------
# ManifestBuilder tests
# ---------------------------------------------------------------------------


class TestManifestBuilder:
    def setup_method(self):
        self.builder = ManifestBuilder()

    def test_build_manifest(self):
        datasets = [_ds(title=f"ds-{i}") for i in range(3)]
        manifest = self.builder.build(datasets)
        assert manifest.version == "1.0"
        assert manifest.generator == "DataScout"
        assert len(manifest.datasets) == 3
        assert manifest.manifest_hash != ""

    def test_manifest_hash_deterministic(self):
        datasets = [_ds(title="same")]
        m1 = self.builder.build(datasets)
        m2 = self.builder.build(datasets)
        assert m1.manifest_hash == m2.manifest_hash

    def test_manifest_hash_changes_with_data(self):
        m1 = self.builder.build([_ds(title="a")])
        m2 = self.builder.build([_ds(title="b")])
        assert m1.manifest_hash != m2.manifest_hash

    def test_download_command_huggingface(self):
        ds = _ds(source="huggingface", title="org/my-dataset")
        cmd = self.builder._generate_download_cmd(ds)
        assert "huggingface-cli" in cmd
        assert "my-dataset" in cmd

    def test_download_command_kaggle(self):
        ds = _ds(source="kaggle")
        cmd = self.builder._generate_download_cmd(ds)
        assert "kaggle" in cmd

    def test_download_command_wget(self):
        ds = _ds(source="openml", download_url="https://openml.org/data/1.arff")
        cmd = self.builder._generate_download_cmd(ds)
        assert "wget" in cmd

    def test_download_command_no_url(self):
        ds = _ds(download_url=None)
        cmd = self.builder._generate_download_cmd(ds)
        assert "No download URL" in cmd


# ---------------------------------------------------------------------------
# ReportGenerator tests
# ---------------------------------------------------------------------------


class TestReportGenerator:
    def setup_method(self):
        self.gen = ReportGenerator()

    def test_generate_report(self):
        query = _q(topic="climate")
        datasets = [_ds(title=f"ds-{i}", score_total=80 - i * 10) for i in range(5)]
        report = self.gen.generate(query, datasets)

        assert report.query.topic == "climate"
        assert report.total_results_found == 5
        assert len(report.top_datasets) == 5
        assert len(report.citations) == 5
        assert report.hash_proof != ""
        assert report.timestamp != ""
        assert report.summary != ""

    def test_top_datasets_sorted_by_score(self):
        query = _q()
        datasets = [
            _ds(title="low", score_total=40),
            _ds(title="high", score_total=90),
            _ds(title="mid", score_total=60),
        ]
        report = self.gen.generate(query, datasets)
        scores = [d.readiness_score.total for d in report.top_datasets]
        assert scores == sorted(scores, reverse=True)

    def test_top_datasets_limited_to_20(self):
        query = _q()
        datasets = [_ds(title=f"ds-{i}") for i in range(25)]
        report = self.gen.generate(query, datasets)
        assert len(report.top_datasets) == 20

    def test_empty_datasets(self):
        report = self.gen.generate(_q(), [])
        assert "No datasets found" in report.summary
        assert report.total_results_found == 0

    def test_comparison_table(self):
        query = _q()
        datasets = [_ds(title=f"ds-{i}") for i in range(5)]
        report = self.gen.generate(query, datasets)
        assert report.comparison_table is not None
        assert len(report.comparison_table.headers) > 0
        assert len(report.comparison_table.rows) == 5

    def test_domain_distribution(self):
        query = _q()
        datasets = [
            _ds(source="huggingface"),
            _ds(source="kaggle"),
            _ds(source="huggingface"),
        ]
        report = self.gen.generate(query, datasets)
        assert "huggingface" in report.domain_distribution or "huggingface" in report.source_distribution

    def test_hash_proof_deterministic(self):
        query = _q(topic="test")
        datasets = [_ds(title="ds-1")]
        r1 = self.gen.generate(query, datasets)
        r2 = self.gen.generate(query, datasets)
        # Hash should be the same since same inputs
        assert r1.hash_proof == r2.hash_proof

    def test_stats_passed(self):
        query = _q()
        datasets = [_ds()]
        stats = {"sources_searched": 10}
        report = self.gen.generate(query, datasets, stats=stats)
        assert report.total_sources_searched == 10

    def test_manifest_in_report(self):
        report = self.gen.generate(_q(), [_ds()])
        assert report.manifest is not None
        assert len(report.manifest.datasets) == 1


# ---------------------------------------------------------------------------
# generate_markdown tests
# ---------------------------------------------------------------------------


class TestGenerateMarkdown:
    def test_basic_markdown(self):
        gen = ReportGenerator()
        datasets = [_ds(title="my-climate-data", score_total=85)]
        report = gen.generate(_q(topic="climate"), datasets)
        md = generate_markdown(report)

        assert "# DataScout Report" in md
        assert "climate" in md
        assert "my-climate-data" in md
        assert "Readiness Score" in md
        assert "Citations" in md

    def test_markdown_with_comparison(self):
        gen = ReportGenerator()
        datasets = [_ds(title=f"ds-{i}", score_total=90 - i * 5) for i in range(3)]
        report = gen.generate(_q(), datasets)
        md = generate_markdown(report)
        assert "Comparison Table" in md

    def test_markdown_empty(self):
        gen = ReportGenerator()
        report = gen.generate(_q(), [])
        md = generate_markdown(report)
        assert "No datasets found" in md

    def test_markdown_manifest_section(self):
        gen = ReportGenerator()
        datasets = [_ds(download_url="https://example.com/download")]
        report = gen.generate(_q(), datasets)
        md = generate_markdown(report)
        assert "Download Manifest" in md
        assert "Manifest Hash" in md

    def test_markdown_proof_of_work(self):
        gen = ReportGenerator()
        report = gen.generate(_q(), [_ds()])
        md = generate_markdown(report)
        assert "Proof of Work" in md
        assert report.hash_proof in md
