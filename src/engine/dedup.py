"""Deduplication engine — detects and merges duplicate datasets across sources."""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

from src.models.dataset import DatasetResult

logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """Detect duplicate datasets across multiple sources and merge them.

    Uses a combination of:
    1. Exact ID matching (same dataset name across sources)
    2. Fuzzy title similarity (SequenceMatcher)
    3. URL similarity (detect mirrors)

    Threshold is set conservatively to avoid false positives.
    """

    # Similarity threshold for considering two datasets as duplicates
    TITLE_THRESHOLD = 0.80
    URL_THRESHOLD = 0.70

    def deduplicate(self, datasets: list[DatasetResult]) -> list[DatasetResult]:
        """Remove duplicates and merge sources.

        Returns a new list where each dataset represents a unique entry,
        with ``merged_from`` tracking all source IDs.
        """
        if not datasets:
            return []

        n = len(datasets)
        # Union-find for grouping duplicates
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Compare all pairs
        for i in range(n):
            for j in range(i + 1, n):
                if self._are_duplicates(datasets[i], datasets[j]):
                    union(i, j)

        # Group by root
        groups: dict[int, list[int]] = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(i)

        # Merge each group
        merged: list[DatasetResult] = []
        for indices in groups.values():
            primary_idx = min(indices, key=lambda k: self._dataset_priority(datasets[k]))
            duplicates = [datasets[k] for k in indices if k != primary_idx]
            merged.append(self._merge_datasets(datasets[primary_idx], duplicates))

        logger.info(
            "Deduplicated %d → %d datasets (%d removed)",
            n, len(merged), n - len(merged),
        )
        return merged

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    def _are_duplicates(self, a: DatasetResult, b: DatasetResult) -> bool:
        """Check if two datasets are likely the same."""
        # Skip if from same source (not a cross-source duplicate)
        if a.source == b.source:
            return False

        # Check title similarity
        title_sim = self._title_similarity(a.title, b.title)
        if title_sim >= self.TITLE_THRESHOLD:
            return True

        # Check URL similarity (same underlying dataset)
        url_sim = self._url_similarity(a.source_url, b.source_url)
        if url_sim >= self.URL_THRESHOLD:
            return True

        # Check if they share a download domain
        if a.download_url and b.download_url:
            if self._extract_domain(a.download_url) == self._extract_domain(b.download_url):
                if title_sim >= 0.6:
                    return True

        return False

    @staticmethod
    def _title_similarity(a: str, b: str) -> float:
        """Compute fuzzy similarity between two titles."""
        a_norm = DeduplicationEngine._normalize_title(a)
        b_norm = DeduplicationEngine._normalize_title(b)

        if not a_norm or not b_norm:
            return 0.0

        return SequenceMatcher(None, a_norm, b_norm).ratio()

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize a title for comparison."""
        t = title.lower().strip()
        # Remove source prefixes like "hf-", "kaggle-", "openml-"
        t = re.sub(r"^(hf|kaggle|openml|zenodo|datagov|fred|noaa|openaq|arxiv|wb)-", "", t)
        # Remove common suffixes
        t = re.sub(r"\s*(dataset|data|collection)$", "", t)
        # Collapse whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t

    @staticmethod
    def _url_similarity(a: str, b: str) -> float:
        """Compute similarity between two URLs (domain + path)."""
        # Compare full URLs normalized
        a_norm = a.rstrip("/").lower()
        b_norm = b.rstrip("/").lower()

        # If domains differ completely, low similarity
        a_domain = DeduplicationEngine._extract_domain(a_norm)
        b_domain = DeduplicationEngine._extract_domain(b_norm)

        if a_domain != b_domain:
            # Different domains → low similarity unless paths match exactly
            return 0.0

        a_path = re.sub(r"https?://[^/]+", "", a_norm).rstrip("/")
        b_path = re.sub(r"https?://[^/]+", "", b_norm).rstrip("/")

        if not a_path or not b_path:
            return 0.0

        return SequenceMatcher(None, a_path, b_path).ratio()

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract the domain from a URL."""
        match = re.match(r"https?://([^/]+)", url)
        return match.group(1) if match else ""

    # ------------------------------------------------------------------
    # Merging
    # ------------------------------------------------------------------

    def _merge_datasets(
        self,
        primary: DatasetResult,
        duplicates: list[DatasetResult],
    ) -> DatasetResult:
        """Merge duplicate datasets into one entry.

        - Keeps the primary's ID and URL
        - Tracks all source IDs in ``merged_from``
        - Picks the best metadata (most rows, best description)
        - Merges tags from all sources
        """
        if not duplicates:
            return primary

        all_ids = [primary.id] + [d.id for d in duplicates]
        all_tags = list(set(primary.tags + [t for d in duplicates for t in d.tags]))

        # Pick best metadata
        best = primary
        for d in duplicates:
            if (d.rows or 0) > (best.rows or 0):
                best = d
            elif (d.rows or 0) == (best.rows or 0):
                # Prefer longer description
                if len(d.description or "") > len(best.description or ""):
                    best = d

        return best.model_copy(
            update={
                "id": primary.id,
                "source_url": primary.source_url,
                "merged_from": all_ids,
                "tags": all_tags,
            }
        )

    @staticmethod
    def _dataset_priority(ds: DatasetResult) -> int:
        """Lower = higher priority for being the primary entry."""
        priority = 0
        if ds.rows:
            priority -= ds.rows  # Prefer datasets with more rows
        if ds.description and len(ds.description) > 100:
            priority -= 1000  # Prefer well-documented datasets
        if ds.download_url:
            priority -= 500
        return priority
