"""Citation formatter — generates APA and BibTeX citations for datasets."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.models.dataset import DatasetResult
from src.models.report import Citation

logger = logging.getLogger(__name__)


class CitationFormatter:
    """Generate academic citations (APA, BibTeX) for datasets."""

    def format_citation(self, dataset: DatasetResult) -> Citation:
        """Generate APA-style citation for a dataset."""
        year = self._extract_year(dataset)
        author = self._get_author(dataset)
        title = dataset.title
        source = self._get_source_name(dataset)
        url = dataset.source_url

        # APA format: Author. (Year). Title. Source. URL
        apa = f"{author}. ({year}). {title}. {source}. {url}"

        return Citation(
            dataset_id=dataset.id,
            apa=apa,
            bibtex=self._to_bibtex(dataset, author, year),
        )

    def format_batch(self, datasets: list[DatasetResult]) -> list[Citation]:
        """Generate citations for a batch of datasets."""
        return [self.format_citation(d) for d in datasets]

    def _extract_year(self, dataset: DatasetResult) -> int:
        """Extract publication year from last_updated or default to current year."""
        if dataset.last_updated:
            try:
                updated = datetime.fromisoformat(
                    dataset.last_updated.replace("Z", "+00:00")
                )
                return updated.year
            except (ValueError, TypeError):
                pass
        return datetime.now(timezone.utc).year

    def _get_author(self, dataset: DatasetResult) -> str:
        """Extract author from dataset title or source."""
        title = dataset.title or ""

        # HuggingFace: "org/dataset-name" → "org"
        if "/" in title:
            author = title.split("/")[0].strip()
            if author:
                return author

        # Use source name as author
        return self._get_source_name(dataset)

    def _get_source_name(self, dataset: DatasetResult) -> str:
        """Get human-readable source name."""
        source_names = {
            "huggingface": "Hugging Face",
            "kaggle": "Kaggle",
            "openml": "OpenML",
            "zenodo": "Zenodo",
            "data_gov": "data.gov",
            "worldbank": "World Bank",
            "fred": "FRED",
            "noaa": "NOAA",
            "openaq": "OpenAQ",
            "arxiv": "arXiv",
        }
        return source_names.get(dataset.source, dataset.source.replace("_", " ").title())

    def _to_bibtex(self, dataset: DatasetResult, author: str, year: int) -> str:
        """Generate BibTeX entry for a dataset."""
        key = dataset.id.replace("-", "_")
        source = self._get_source_name(dataset)

        return (
            f"@misc{{{key},\n"
            f"  author = {{{author}}},\n"
            f"  year = {{{year}}},\n"
            f"  title = {{{dataset.title}}},\n"
            f"  publisher = {{{source}}},\n"
            f"  url = {{{dataset.source_url}}},\n"
            f"}}"
        )
