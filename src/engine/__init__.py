"""DataScout engine — orchestration, deduplication, ranking, license, profiling, and scoring."""

from src.engine.dedup import DeduplicationEngine
from src.engine.license import LicenseExtractor
from src.engine.orchestrator import SearchOrchestrator, SearchStats, create_default_orchestrator
from src.engine.profiler import DataProfiler
from src.engine.ranking import RankingEngine
from src.engine.score import ReadinessCalculator

__all__ = [
    "SearchOrchestrator",
    "SearchStats",
    "create_default_orchestrator",
    "DeduplicationEngine",
    "LicenseExtractor",
    "RankingEngine",
    "DataProfiler",
    "ReadinessCalculator",
]
