"""Dataset search adapters — unified interface for multiple data sources."""

from src.adapters.base import BaseSearchAdapter
from src.adapters.arxiv import ArXivAdapter
from src.adapters.data_gov import DataGovAdapter
from src.adapters.fred import FredAdapter
from src.adapters.huggingface import HuggingFaceAdapter
from src.adapters.kaggle import KaggleAdapter
from src.adapters.noaa import NOAAAdapter
from src.adapters.openaq import OpenAQAdapter
from src.adapters.openml import OpenMLAdapter
from src.adapters.worldbank import WorldBankAdapter
from src.adapters.zenodo import ZenodoAdapter

__all__ = [
    "BaseSearchAdapter",
    "HuggingFaceAdapter",
    "KaggleAdapter",
    "FredAdapter",
    "OpenMLAdapter",
    "ZenodoAdapter",
    "DataGovAdapter",
    "WorldBankAdapter",
    "NOAAAdapter",
    "OpenAQAdapter",
    "ArXivAdapter",
]
