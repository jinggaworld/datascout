"""Report generator — builds final reports with rankings, citations, and manifests."""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from datetime import datetime, timezone

from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery
from src.models.report import FinalReport, DatasetComparison
from src.report.citations import CitationFormatter
from src.report.manifest import ManifestBuilder

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate final DataScout reports from processed search results."""

    def __init__(self) -> None:
        self.citation_formatter = CitationFormatter()
        self.manifest_builder = ManifestBuilder()

    def generate(
        self,
        query: ParsedQuery,
        datasets: list[DatasetResult],
        stats: dict | None = None,
    ) -> FinalReport:
        """Build a complete FinalReport from processed results.

        Args:
            query: The original parsed query.
            datasets: Ranked, deduplicated, scored datasets.
            stats: Optional search stats from the orchestrator.

        Returns:
            A complete FinalReport with citations, manifest, and summary.
        """
        # Ensure datasets are sorted by readiness score
        sorted_ds = self._sort_datasets(datasets)

        # Limit to top 20
        top_datasets = sorted_ds[:20]

        # Build components
        citations = self.citation_formatter.format_batch(top_datasets)
        manifest = self.manifest_builder.build(top_datasets)
        comparison = self._build_comparison(top_datasets)
        domain_dist = self._distribution(top_datasets, "domain")
        source_dist = self._distribution(top_datasets, "source")
        summary = self._build_summary(query, datasets, stats)

        # Compute hash proof
        hash_proof = self._compute_hash_proof(query, top_datasets)

        # Stats
        sources_searched = stats.get("sources_searched", 0) if stats else 0

        report = FinalReport(
            query=query,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_sources_searched=sources_searched,
            total_results_found=len(datasets),
            deduped_results=len(datasets),
            top_datasets=top_datasets,
            comparison_table=comparison,
            summary=summary,
            domain_distribution=domain_dist,
            source_distribution=source_dist,
            citations=citations,
            manifest=manifest,
            hash_proof=hash_proof,
        )

        logger.info(
            "Report generated: %d datasets, %d citations, hash=%s",
            len(top_datasets),
            len(citations),
            hash_proof[:12],
        )

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sort_datasets(self, datasets: list[DatasetResult]) -> list[DatasetResult]:
        """Sort datasets by readiness score descending, then by relevance."""
        return sorted(
            datasets,
            key=lambda d: (
                d.readiness_score.total if d.readiness_score else 0,
                d.relevance_score,
            ),
            reverse=True,
        )

    def _build_comparison(self, datasets: list[DatasetResult]) -> DatasetComparison:
        """Build a side-by-side comparison table for top datasets."""
        headers = [
            "Rank", "Title", "Source", "Rows", "Score", "Grade", "License", "Format"
        ]

        rows: list[list[str]] = []
        for i, d in enumerate(datasets[:10], 1):
            score_str = f"{d.readiness_score.total:.0f}" if d.readiness_score else "N/A"
            grade = d.readiness_score.grade if d.readiness_score else "N/A"
            license_name = d.license_status.license_name if d.license_status and d.license_status.detected else "Unknown"
            rows.append([
                str(i),
                d.title[:40] + ("..." if len(d.title) > 40 else ""),
                d.source,
                f"{d.rows:,}" if d.rows else "N/A",
                score_str,
                grade,
                license_name or "Unknown",
                d.file_format or "N/A",
            ])

        return DatasetComparison(headers=headers, rows=rows)

    def _distribution(self, datasets: list[DatasetResult], field: str) -> dict[str, int]:
        """Count occurrences of a field value across datasets."""
        counter: Counter[str] = Counter()
        for d in datasets:
            value = getattr(d, field, "other")
            counter[value] += 1
        return dict(counter.most_common())

    def _build_summary(
        self,
        query: ParsedQuery,
        datasets: list[DatasetResult],
        stats: dict | None,
    ) -> str:
        """Build a human-readable summary of the search results."""
        n = len(datasets)
        if n == 0:
            return f"No datasets found for query: {query.topic}"

        # Count sources
        sources = set(d.source for d in datasets)
        # Find best dataset
        best = max(
            datasets,
            key=lambda d: d.readiness_score.total if d.readiness_score else 0,
        )
        best_score = best.readiness_score.total if best.readiness_score else 0

        # Count license types
        licensed = sum(
            1 for d in datasets
            if d.license_status and d.license_status.detected
        )

        parts = [
            f"Found {n} datasets matching '{query.topic}'",
            f"from {len(sources)} sources ({', '.join(sorted(sources))}).",
        ]

        if best_score > 0:
            parts.append(
                f"Best match: '{best.title}' (score: {best_score:.0f}/100, grade: {best.readiness_score.grade})."
            )

        if licensed > 0:
            parts.append(f"{licensed} of {n} datasets have detected licenses.")

        if query.region:
            parts.append(f"Filtered by region: {query.region}.")

        return " ".join(parts)

    def _compute_hash_proof(
        self,
        query: ParsedQuery,
        datasets: list[DatasetResult],
    ) -> str:
        """Compute a deterministic SHA-256 hash proof of the work done."""
        # Build a deterministic string from query + dataset IDs
        parts = [
            query.topic,
            query.domain,
            ",".join(sorted(query.keywords)),
            ",".join(d.id for d in datasets),
        ]
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()


def generate_markdown(report: FinalReport) -> str:
    """Convert a FinalReport to a human-readable Markdown string."""
    q = report.query

    md = f"""# DataScout Report

**Query:** {q.topic}
**Keywords:** {', '.join(q.keywords) if q.keywords else 'N/A'}
**Domain:** {q.domain}
**Region:** {q.region or 'Global'}
**Date:** {report.timestamp[:10] if report.timestamp else 'N/A'}

---

## Summary

{report.summary}

Searched **{report.total_sources_searched}** sources, found **{report.total_results_found}** datasets, **{report.deduped_results}** after deduplication.

---

## Top Datasets

"""

    for i, d in enumerate(report.top_datasets[:10], 1):
        score_str = f"{d.readiness_score.total:.0f}/100 ({d.readiness_score.grade})" if d.readiness_score else "N/A"
        license_name = d.license_status.license_name if d.license_status and d.license_status.detected else "Unknown"
        rows_str = f"{d.rows:,}" if d.rows else "N/A"

        md += f"""### {i}. {d.title}

- **Source:** {d.source}
- **Readiness Score:** {score_str}
- **License:** {license_name}
- **Rows:** {rows_str}
- **Format:** {d.file_format or 'N/A'}
- **URL:** {d.source_url}        {re.sub(r'<[^>]*>', '', d.description)[:200] if d.description else 'No description available.'}

"""

    # Comparison table
    if report.comparison_table and report.comparison_table.rows:
        md += "---\n\n## Comparison Table\n\n"
        md += "| " + " | ".join(report.comparison_table.headers) + " |\n"
        md += "| " + " | ".join(["---"] * len(report.comparison_table.headers)) + " |\n"
        for row in report.comparison_table.rows:
            md += "| " + " | ".join(row) + " |\n"
        md += "\n"

    # Citations
    if report.citations:
        md += "---\n\n## Citations\n\n"
        for c in report.citations[:5]:
            md += f"```\n{c.apa}\n```\n\n"

    # Manifest
    if report.manifest and report.manifest.datasets:
        md += "---\n\n## Download Manifest\n\n"
        md += f"**Manifest Hash:** `{report.manifest.manifest_hash[:16]}...`\n\n"
        for entry in report.manifest.datasets[:5]:
            md += f"### {entry.title}\n"
            md += f"- Source: {entry.source}\n"
            md += f"- Command: `{entry.download_command}`\n\n"

    # Hash proof
    md += f"""---

## Proof of Work

**Hash:** `{report.hash_proof}`

*Generated by DataScout — Automated Dataset Discovery Agent*
"""

    return md
