import hashlib
import json
import logging
import time
from typing import Any

from src.models.cap import CapDelivery
from src.models.report import FinalReport

logger = logging.getLogger(__name__)


def format_delivery(
    order_id: str,
    agent_id: str,
    report: FinalReport,
    execution_time_ms: int = 0,
) -> CapDelivery:
    """Format a FinalReport into a CAP delivery payload."""
    report_dict = report.model_dump()
    report_json = json.dumps(report_dict, sort_keys=True, default=str)
    hash_proof = hashlib.sha256(report_json.encode()).hexdigest()

    delivery = CapDelivery(
        order_id=order_id,
        agent_id=agent_id,
        report_json=report_dict,
        report_markdown=report.summary,
        hash_proof=hash_proof,
        datasets_found=report.deduped_results,
        sources_searched=report.total_sources_searched,
        execution_time_ms=execution_time_ms,
        model_used=report.query.model_used if hasattr(report.query, "model_used") else "",
    )

    logger.info(
        "Delivery formatted: order=%s, datasets=%d, hash=%s...",
        order_id,
        delivery.datasets_found,
        hash_proof[:16],
    )
    return delivery


def generate_hash_proof(data: dict[str, Any]) -> str:
    """Generate SHA-256 hash proof for any data payload."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()
