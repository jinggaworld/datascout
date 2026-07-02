"""Dataset search adapters — unified interface for multiple data sources."""

from src.adapters.base import BaseSearchAdapter
from src.adapters.fred import FredAdapter
from src.adapters.huggingface import HuggingFaceAdapter
from src.adapters.kaggle import KaggleAdapter

__all__ = [
    "BaseSearchAdapter",
    "HuggingFaceAdapter",
    "KaggleAdapter",
    "FredAdapter",
]
