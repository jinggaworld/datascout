"""Data profiling engine — extracts schema, statistics, and previews from datasets."""

from __future__ import annotations

import logging
from typing import Any

from src.models.dataset import DataPreview, DataProfile, DatasetResult

logger = logging.getLogger(__name__)


class DataProfiler:
    """Profile dataset content: schema, statistics, missing values, and sample rows.

    Works with pandas DataFrames. Can be used standalone or as part of
    the search pipeline to enrich DatasetResult models with preview data.
    """

    MAX_SAMPLE_ROWS = 10

    def profile(
        self,
        dataset: DatasetResult,
        df: Any | None = None,
    ) -> DatasetResult:
        """Add profiling info to a DatasetResult.

        Args:
            dataset: The dataset to enrich.
            df: A pandas DataFrame with the dataset content.
                If None, returns the dataset unchanged.

        Returns:
            Copy of the dataset with preview and profile populated.
        """
        if df is None or not hasattr(df, "columns"):
            return dataset

        try:
            import pandas as pd

            preview = self._create_preview(df, pd)
            profile = self._create_profile(df, pd)

            return dataset.model_copy(update={
                "preview": preview,
                "data_profile": profile,
            })
        except Exception as exc:
            logger.warning("Failed to profile dataset %s: %s", dataset.id, exc)
            return dataset

    def profile_from_dicts(
        self,
        dataset: DatasetResult,
        rows: list[dict[str, Any]],
    ) -> DatasetResult:
        """Profile from a list of dicts (e.g., JSON API response)."""
        if not rows:
            return dataset

        try:
            import pandas as pd

            df = pd.DataFrame(rows)
            return self.profile(dataset, df)
        except Exception as exc:
            logger.warning("Failed to profile from dicts: %s", exc)
            return dataset

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _create_preview(self, df: Any, pd: Any) -> DataPreview:
        """Create a data preview with column info and sample rows."""
        sample = df.head(self.MAX_SAMPLE_ROWS)

        columns: list[dict[str, Any]] = []
        for col in df.columns:
            col_info: dict[str, Any] = {
                "name": str(col),
                "dtype": str(df[col].dtype),
                "sample_values": [
                    _safe_serialize(v) for v in df[col].head(3).tolist()
                ],
                "null_count": int(df[col].isnull().sum()),
                "null_percentage": round(float(df[col].isnull().mean()) * 100, 2),
                "unique_count": int(df[col].nunique()),
            }

            # Add numeric-specific stats
            if pd.api.types.is_numeric_dtype(df[col]) and not df[col].isnull().all():
                col_info["min"] = _safe_serialize(df[col].min())
                col_info["max"] = _safe_serialize(df[col].max())
                col_info["mean"] = _safe_serialize(round(float(df[col].mean()), 4))

            columns.append(col_info)

        sample_rows: list[dict[str, Any]] = []
        for _, row in sample.iterrows():
            sample_rows.append({
                col: _safe_serialize(val) for col, val in row.items()
            })

        return DataPreview(
            columns=columns,
            sample_rows=sample_rows,
            total_rows=len(df),
            total_columns=len(df.columns),
        )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def _create_profile(self, df: Any, pd: Any) -> DataProfile:
        """Create a statistical profile of the dataset."""
        numeric_stats: dict[str, Any] = {}
        categorical_stats: dict[str, Any] = {}

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]) and not df[col].isnull().all():
                numeric_stats[str(col)] = {
                    "mean": _safe_serialize(round(float(df[col].mean()), 4)),
                    "median": _safe_serialize(round(float(df[col].median()), 4)),
                    "std": _safe_serialize(round(float(df[col].std()), 4)),
                    "min": _safe_serialize(df[col].min()),
                    "max": _safe_serialize(df[col].max()),
                    "q25": _safe_serialize(df[col].quantile(0.25)),
                    "q75": _safe_serialize(df[col].quantile(0.75)),
                    "null_count": int(df[col].isnull().sum()),
                }
            else:
                value_counts = df[col].value_counts().head(10)
                categorical_stats[str(col)] = {
                    "unique_count": int(df[col].nunique()),
                    "top_values": {
                        str(k): int(v) for k, v in value_counts.items()
                    },
                    "null_count": int(df[col].isnull().sum()),
                    "null_percentage": round(float(df[col].isnull().mean()) * 100, 2),
                }

        # Missing value summary
        total_cells = int(df.size)
        total_missing = int(df.isnull().sum().sum())
        missing_cols = [str(c) for c in df.columns if df[c].isnull().any()]

        missing_summary = {
            "total_cells": total_cells,
            "total_missing": total_missing,
            "missing_percentage": round(
                (total_missing / total_cells * 100) if total_cells > 0 else 0, 2
            ),
            "columns_with_missing": missing_cols,
        }

        return DataProfile(
            numeric_stats=numeric_stats,
            categorical_stats=categorical_stats,
            missing_summary=missing_summary,
        )


def _safe_serialize(value: Any) -> Any:
    """Safely serialize a value for JSON output."""
    import math

    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if hasattr(value, "item"):  # numpy scalar
        return value.item()
    return value
