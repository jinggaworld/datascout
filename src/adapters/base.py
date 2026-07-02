"""Abstract base adapter for dataset search sources."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.models.dataset import DatasetResult
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)


class BaseSearchAdapter(ABC):
    """Abstract base class for all dataset search adapters.

    Each adapter wraps a data source (HuggingFace, Kaggle, etc.) and
    exposes a unified search interface that returns DatasetResult models.
    """

    SOURCE_NAME: str = ""
    BASE_URL: str = ""

    @abstractmethod
    async def search(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DatasetResult]:
        """Search for datasets matching the parsed query.

        Args:
            parsed_query: Structured query from the AI parser.
            limit: Maximum number of results to return.
            offset: Pagination offset.

        Returns:
            List of DatasetResult models, possibly empty on no matches.
        """
        ...

    async def health_check(self) -> bool:
        """Check if the data source is reachable. Override as needed."""
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source={self.SOURCE_NAME!r}>"
