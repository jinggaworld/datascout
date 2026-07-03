"""Download proxy — fetch dataset data from source APIs, convert to CSV/JSON."""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Timeout for source API calls
SOURCE_TIMEOUT = 30


async def fetch_source_data(download_url: str, source: str) -> dict[str, Any]:
    """Fetch raw data from a source API and return normalized records.

    Returns:
        {
            "columns": [{"name": str, "type": str}],
            "rows": [dict, ...],
            "total_rows": int,
            "raw_data": any,  # original parsed response
        }
    """
    try:
        async with httpx.AsyncClient(timeout=SOURCE_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to fetch data from %s: %s", download_url, e)
        return {"columns": [], "rows": [], "total_rows": 0, "raw_data": None}

    content_type = resp.headers.get("content-type", "")
    text = resp.text

    # Try JSON first
    if "json" in content_type or text.lstrip().startswith(("{", "[")):
        try:
            data = json.loads(text)
            return _normalize_json(data, source)
        except json.JSONDecodeError:
            pass

    # Try CSV
    if "csv" in content_type or "text/" in content_type:
        try:
            return _normalize_csv(text)
        except Exception:
            pass

    # Fallback: return raw text
    return {
        "columns": [{"name": "raw", "type": "string"}],
        "rows": [{"raw": text[:50000]}],
        "total_rows": 1,
        "raw_data": text[:100000],
    }


def _normalize_json(data: Any, source: str) -> dict[str, Any]:
    """Normalize various JSON structures into rows + columns."""
    # World Bank format: [metadata, data_array]
    if isinstance(data, list) and len(data) >= 2 and isinstance(data[0], dict) and isinstance(data[1], list):
        records = data[1]
        if isinstance(records, list) and len(records) > 0 and isinstance(records[0], dict):
            return _dict_list_to_table(records)
        return {"columns": [], "rows": [], "total_rows": 0, "raw_data": data}

    # Plain array of objects
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        return _dict_list_to_table(data)

    # Single object with nested data
    if isinstance(data, dict):
        # Look for a nested list
        for key, val in data.items():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                return _dict_list_to_table(val)
        # Flat object → single row
        return {
            "columns": [{"name": str(k), "type": _infer_type(v)} for k, v in data.items()],
            "rows": [data],
            "total_rows": 1,
            "raw_data": data,
        }

    return {"columns": [], "rows": [], "total_rows": 0, "raw_data": data}


def _dict_list_to_table(records: list[dict]) -> dict[str, Any]:
    """Convert list of dicts to column definitions + rows."""
    # Collect all keys
    all_keys: list[str] = []
    seen: set[str] = set()
    for r in records:
        for k in r:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    columns = [{"name": k, "type": _infer_type(next((r[k] for r in records if k in r), None))} for k in all_keys]
    return {
        "columns": columns,
        "rows": records[:1000],  # limit to 1000 rows for preview
        "total_rows": len(records),
        "raw_data": None,
    }


def _normalize_csv(text: str) -> dict[str, Any]:
    """Parse CSV text into columns + rows."""
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    columns = []
    fieldnames = reader.fieldnames or []

    for i, row in enumerate(reader):
        if i == 0:
            columns = [{"name": fn, "type": _infer_type(row.get(fn))} for fn in fieldnames]
        rows.append(dict(row))
        if len(rows) >= 1000:
            break

    return {
        "columns": columns,
        "rows": rows,
        "total_rows": len(rows),
        "raw_data": None,
    }


def _infer_type(value: Any) -> str:
    """Infer a simple type string for a value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def rows_to_csv(columns: list[dict], rows: list[dict]) -> str:
    """Convert columns + rows to CSV string."""
    if not columns or not rows:
        return ""
    fieldnames = [c["name"] for c in columns]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def rows_to_json(columns: list[dict], rows: list[dict], total_rows: int) -> str:
    """Convert columns + rows to pretty-printed JSON."""
    return json.dumps(
        {
            "columns": [c["name"] for c in columns],
            "total_rows": total_rows,
            "data": rows,
        },
        indent=2,
        default=str,
    )
