"""Dataset search adapters — unified interface for multiple data sources."""

from src.adapters.base import BaseSearchAdapter
from src.adapters.huggingface import HuggingFaceAdapter

__all__ = [
    "BaseSearchAdapter",
    "HuggingFaceAdapter",
]
