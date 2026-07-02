import logging

from src.models.cap import CapNegotiation
from src.models.query import ParsedQuery

logger = logging.getLogger(__name__)

# Base pricing in USDC
BASE_PRICE = 0.01
COST_PER_SOURCE = 0.002
MIN_ROWS_COST = 0.005
TIME_RANGE_COST = 0.005
LICENSE_FILTER_COST = 0.005

# Estimated sources per region scope
SOURCES_GLOBAL = 15
SOURCES_REGIONAL = 8


def estimate_price(parsed_query: ParsedQuery) -> CapNegotiation:
    """Estimate price in USDC based on query complexity.

    Pricing factors:
    - Base price per query
    - Number of data sources to search
    - Extra filters (min_rows, time_range, license)
    """
    source_count = SOURCES_GLOBAL if not parsed_query.region else SOURCES_REGIONAL
    source_cost = source_count * COST_PER_SOURCE

    extras_cost = 0.0
    extras = []
    if parsed_query.min_rows:
        extras_cost += MIN_ROWS_COST
        extras.append(f"size filter ({parsed_query.min_rows}+ rows)")
    if parsed_query.time_range:
        extras_cost += TIME_RANGE_COST
        extras.append("time range filter")
    if parsed_query.license.value != "any":
        extras_cost += LICENSE_FILTER_COST
        extras.append(f"license filter ({parsed_query.license.value})")

    total = BASE_PRICE + source_cost + extras_cost
    estimated_time = max(10, source_count * 2 // 3)

    description = (
        f"Search {source_count} sources for '{parsed_query.topic}'"
        f" | {len(extras)} extra filters"
        if extras
        else f"Search {source_count} sources for '{parsed_query.topic}'"
    )

    logger.info("Price estimate: %.4f USDC — %s", total, description)

    return CapNegotiation(
        base_price_usdc=BASE_PRICE,
        source_count=source_count,
        source_cost_usdc=round(source_cost, 4),
        extras_cost_usdc=round(extras_cost, 4),
        total_price_usdc=round(total, 4),
        estimated_search_time_sec=estimated_time,
        description=description,
    )
