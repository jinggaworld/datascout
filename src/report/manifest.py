"""Manifest builder — creates reproducible download manifests with SHA-256 hashes."""

from __future__ import annotations

import hashlib
import json
import logging

from src.models.dataset import DatasetResult
from src.models.report import Manifest, ManifestEntry

logger = logging.getLogger(__name__)


class ManifestBuilder:
    """Build reproducible download manifests for datasets."""

    def build(self, datasets: list[DatasetResult]) -> Manifest:
        """Build a reproducible download manifest.

        Each entry includes download URL, source info, and a shell
        command to reproduce the download.
        """
        entries: list[ManifestEntry] = []
        for d in datasets:
            entry = ManifestEntry(
                dataset_id=d.id,
                title=d.title,
                source=d.source,
                download_url=d.download_url,
                source_url=d.source_url,
                file_format=d.file_format,
                checksum_algorithm="sha256",
                download_command=self._generate_download_cmd(d),
            )
            entries.append(entry)

        # Generate deterministic manifest hash
        manifest_json = json.dumps(
            [e.model_dump() for e in entries],
            sort_keys=True,
            separators=(",", ":"),
        )
        manifest_hash = hashlib.sha256(manifest_json.encode()).hexdigest()

        return Manifest(
            version="1.0",
            generator="DataScout",
            datasets=entries,
            manifest_hash=manifest_hash,
        )

    def _generate_download_cmd(self, dataset: DatasetResult) -> str:
        """Generate a shell command to download the dataset."""
        if not dataset.download_url:
            return "# No download URL available"

        source = dataset.source
        url = dataset.download_url

        if source == "huggingface":
            name = dataset.title.split("/")[-1] if "/" in dataset.title else dataset.title
            return f"huggingface-cli download {name}"
        elif source == "kaggle":
            ref = dataset.id.replace("kaggle-", "")
            return f"kaggle datasets download -d {ref}"
        elif source == "arxiv":
            return f"wget {url}"
        elif source in ("fred", "worldbank", "noaa"):
            return f'curl -o "{dataset.id}.json" "{url}"'
        else:
            return f"wget -O {dataset.id}.{dataset.file_format or 'dat'} {url}"
