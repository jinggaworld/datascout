"""Relevance ranking engine — scores and ranks datasets against a parsed query."""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone

from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)


class RankingEngine:
    """Rank datasets by relevance to a parsed query.

    Uses a weighted scoring formula combining:
    - Keyword relevance (0.45) — title/description match to query
    - Freshness (0.15) — newer datasets score higher
    - Size (0.15) — larger datasets score higher (log scale)
    - Documentation (0.15) — description quality & tags
    - Source diversity (0.10) — bonus for less-common sources
    """

    # Weights for each scoring component
    W_RELEVANCE = 0.45
    W_FRESHNESS = 0.15
    W_SIZE = 0.15
    W_DOCS = 0.15
    W_SOURCE = 0.10

    def rank(
        self,
        query: ParsedQuery,
        datasets: list[DatasetResult],
    ) -> list[DatasetResult]:
        """Rank datasets by relevance to the parsed query.

        Returns a new list sorted by descending relevance score.
        Each dataset's ``relevance_score`` field is updated.
        """
        if not datasets:
            return []

        # Precompute query tokens
        query_tokens = self._tokenize(
            f"{query.topic} {' '.join(query.keywords)} {query.domain}"
        )

        # Compute scores
        scored: list[tuple[float, DatasetResult]] = []
        for ds in datasets:
            score = self._compute_score(query_tokens, query, ds)
            scored.append((score, ds))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Update relevance_score and return
        ranked: list[DatasetResult] = []
        for score, ds in scored:
            ranked.append(
                ds.model_copy(update={"relevance_score": round(min(1.0, max(0.0, score)), 4)})
            )

        return ranked

    # ------------------------------------------------------------------
    # Scoring components
    # ------------------------------------------------------------------

    def _compute_score(
        self,
        query_tokens: set[str],
        query: ParsedQuery,
        dataset: DatasetResult,
    ) -> float:
        """Compute the final weighted relevance score."""
        r = self._keyword_score(query_tokens, dataset)
        f = self._freshness_score(dataset)
        s = self._size_score(dataset)
        d = self._doc_score(dataset)
        src = self._source_score(dataset)

        return (
            r * self.W_RELEVANCE
            + f * self.W_FRESHNESS
            + s * self.W_SIZE
            + d * self.W_DOCS
            + src * self.W_SOURCE
        )

    def _keyword_score(self, query_tokens: set[str], dataset: DatasetResult) -> float:
        """Score based on token overlap between query and dataset text."""
        if not query_tokens:
            return 0.0

        ds_text = f"{dataset.title} {dataset.description} {' '.join(dataset.tags)}"
        ds_tokens = self._tokenize(ds_text)

        if not ds_tokens:
            return 0.0

        # Jaccard-like overlap weighted by title matches
        overlap = query_tokens & ds_tokens
        base = len(overlap) / len(query_tokens) if query_tokens else 0.0

        # Bonus for title match (titles matter more)
        title_tokens = self._tokenize(dataset.title or "")
        title_overlap = query_tokens & title_tokens
        title_bonus = 0.3 if title_overlap else 0.0

        return min(1.0, base + title_bonus)

    def _freshness_score(self, dataset: DatasetResult) -> float:
        """Score based on last update date. Newer = higher."""
        if not dataset.last_updated:
            return 0.5  # Unknown age → neutral

        try:
            updated = datetime.fromisoformat(
                dataset.last_updated.replace("Z", "+00:00")
            )
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - updated).days
            # Linear decay over 2 years, floor at 0.1
            return max(0.1, 1.0 - (days_ago / 730))
        except (ValueError, TypeError):
            return 0.5

    def _size_score(self, dataset: DatasetResult) -> float:
        """Score based on dataset size (log scale)."""
        if not dataset.rows or dataset.rows <= 0:
            return 0.5  # Unknown size → neutral
        # Log10 scale: 10 rows → 1.0, 100M rows → 8.0 → normalized to ~1.0
        return min(1.0, math.log10(max(dataset.rows, 1)) / 8)

    def _doc_score(self, dataset: DatasetResult) -> float:
        """Score based on documentation quality."""
        score = 0.3  # Base score

        desc = dataset.description or ""
        if len(desc) > 200:
            score += 0.25
        elif len(desc) > 50:
            score += 0.15

        tags = dataset.tags or []
        if len(tags) >= 3:
            score += 0.2
        elif len(tags) >= 1:
            score += 0.1

        if dataset.download_url:
            score += 0.15

        if dataset.file_format:
            score += 0.1

        return min(1.0, score)

    def _source_score(self, dataset: DatasetResult) -> float:
        """Score based on source trustworthiness and diversity."""
        # Well-known sources get higher trust score
        well_known = {"huggingface", "kaggle", "data_gov", "worldbank"}
        if dataset.source in well_known:
            return 0.8
        # Niche sources get a moderate score (diversity bonus)
        return 0.6

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Lowercase, strip punctuation, split into tokens."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = set(text.split())
        # Remove very short tokens
        return {t for t in tokens if len(t) > 1}
