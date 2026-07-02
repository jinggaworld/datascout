"""DataScout engine — orchestration, deduplication, and ranking."""

from src.engine.orchestrator import SearchOrchestrator, SearchStats, create_default_orchestrator

__all__ = [
    "SearchOrchestrator",
    "SearchStats",
    "create_default_orchestrator",
]
