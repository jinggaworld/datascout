"""Kaggle dataset search adapter — uses the Kaggle CLI for dataset discovery."""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import shutil
import subprocess

from src.adapters.base import BaseSearchAdapter
from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain mapping: Kaggle tags → DataScout domain
# ---------------------------------------------------------------------------

_KAGGLE_TAG_TO_DOMAIN: dict[str, str] = {
    "finance": "finance",
    "health": "health",
    "medical": "health",
    "climate": "climate",
    "weather": "climate",
    "nlp": "nlp",
    "text": "nlp",
    "computer vision": "cv",
    "image": "cv",
    "audio": "audio",
    "speech": "audio",
    "time series": "time_series",
    "tabular": "tabular",
    "social science": "social",
    "social media": "social",
    "geospatial": "geospatial",
    "education": "education",
}


class KaggleAdapter(BaseSearchAdapter):
    """Search datasets on Kaggle using the CLI.

    Requires KAGGLE_USERNAME and KAGGLE_KEY environment variables.
    If the Kaggle CLI is not installed or credentials are missing,
    search returns an empty list with a warning.
    """

    SOURCE_NAME = "kaggle"
    DEFAULT_TIMEOUT = 30  # seconds

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        """Search Kaggle for datasets matching the parsed query."""
        if not self._cli_available():
            logger.warning("Kaggle CLI not found — skipping Kaggle search")
            return []

        cmd = self._build_command(parsed_query, limit)
        logger.debug("Running: %s", " ".join(cmd))

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=self.DEFAULT_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            logger.error("Kaggle CLI timed out after %ds", self.DEFAULT_TIMEOUT)
            return []
        except FileNotFoundError:
            logger.warning("Kaggle CLI not found — skipping")
            return []

        if result.returncode != 0:
            stderr = result.stderr.strip()
            # Graceful handling when credentials are missing
            if "Could not find" in stderr or "credentials" in stderr.lower():
                logger.warning("Kaggle credentials not configured: %s", stderr)
            else:
                logger.error("Kaggle CLI error (code %d): %s", result.returncode, stderr)
            return []

        stdout = result.stdout.strip()
        if not stdout:
            logger.info("Kaggle returned 0 results for query: %s", parsed_query.topic)
            return []

        results = self._parse_csv_output(stdout, parsed_query)
        logger.info("Kaggle returned %d results", len(results))
        return results

    async def health_check(self) -> bool:
        """Check if the Kaggle CLI is available and credentials are set."""
        return self._cli_available()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cli_available(self) -> bool:
        """Check if the kaggle CLI is on PATH."""
        return shutil.which("kaggle") is not None

    def _build_command(self, parsed_query: ParsedQuery, limit: int) -> list[str]:
        """Build the kaggle CLI command."""
        # Combine topic + first 3 keywords as search terms
        search_terms = [parsed_query.topic] + parsed_query.keywords[:3]
        search_query = " ".join(search_terms)

        cmd = [
            "kaggle",
            "datasets",
            "list",
            "-s",
            search_query,
            "--csv",
            "-p",
            str(limit),
        ]

        # Add file-type filter if specified
        if parsed_query.format:
            cmd.extend(["--file-type", parsed_query.format[0]])

        return cmd

    def _parse_csv_output(self, stdout: str, parsed_query: ParsedQuery) -> list[DatasetResult]:
        """Parse the Kaggle CLI CSV output into DatasetResult models."""
        reader = csv.DictReader(io.StringIO(stdout))
        results: list[DatasetResult] = []

        for row in reader:
            try:
                results.append(self._parse_row(row, parsed_query))
            except Exception as exc:
                logger.debug("Skipping malformed Kaggle row: %s", exc)
                continue

        return results

    def _parse_row(self, row: dict[str, str], parsed_query: ParsedQuery) -> DatasetResult:
        """Convert a single Kaggle CSV row to a DatasetResult."""
        ref: str = row.get("ref", "")
        name: str = row.get("name", ref)
        subtitle: str = row.get("subtitle", "")
        total_bytes_str: str = row.get("totalBytes", "")
        file_type: str = row.get("fileType", "csv")
        tags_raw: str = row.get("tags", "")
        last_updated: str = row.get("lastUpdated", "")

        # Parse file size
        file_size_mb: float | None = None
        try:
            if total_bytes_str:
                file_size_mb = float(total_bytes_str) / 1_000_000
        except (ValueError, TypeError):
            pass

        # Parse tags
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        # Infer domain from tags
        domain = self._infer_domain(tags, parsed_query.domain)

        return DatasetResult(
            id=f"kaggle-{ref}",
            title=name or ref,
            description=subtitle,
            source=self.SOURCE_NAME,
            source_url=f"https://www.kaggle.com/datasets/{ref}",
            download_url=f"https://www.kaggle.com/api/v1/datasets/download/{ref}",
            rows=None,
            columns=None,
            file_size_mb=file_size_mb,
            file_format=file_type or "csv",
            last_updated=last_updated or None,
            tags=tags,
            domain=domain,
            region=None,
        )

    def _infer_domain(self, tags: list[str], fallback_domain: str) -> str:
        """Infer DataScout domain from Kaggle tags."""
        tags_lower = [t.lower() for t in tags]
        for tag in tags_lower:
            if tag in _KAGGLE_TAG_TO_DOMAIN:
                return _KAGGLE_TAG_TO_DOMAIN[tag]
        return fallback_domain or "other"
