"""Build the Parquet deliverable from parsed JSONL.

The Dataverse CSVs published in 2014-2023 came from an earlier parser with a
flat, per-run column set. New runs produce the record shape in
:mod:`archive_news_cc.parse`; this module writes it under an explicit schema so
types survive into pandas, R arrow and DuckDB without guessing.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.parquet as pq

from archive_news_cc.common import iter_json_lines

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA = pa.schema(
    [
        pa.field("identifier", pa.string(), nullable=False),
        pa.field("title", pa.string()),
        pa.field("contributor", pa.string()),
        pa.field("aired_date", pa.date32()),
        pa.field("publicdate", pa.string()),
        pa.field("description", pa.string()),
        pa.field("language", pa.string()),
        pa.field("runtime", pa.string()),
        pa.field("closed_captioning", pa.string()),
        pa.field("text", pa.string()),
        pa.field("wordcount", pa.int32()),
        pa.field("caption_empty", pa.bool_()),
        pa.field("extra_json", pa.string()),
        pa.field("source", pa.string(), nullable=False),
    ]
)


def _aired(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def to_row(record: dict[str, Any], source: str) -> dict[str, Any]:
    """Map one parsed record onto :data:`SCHEMA`."""
    text = record.get("text") or ""
    return {
        "identifier": record["identifier"],
        "title": record.get("title"),
        "contributor": record.get("contributor"),
        "aired_date": _aired(record.get("date")),
        "publicdate": record.get("publicdate"),
        "description": record.get("description"),
        "language": record.get("language"),
        "runtime": record.get("runtime"),
        "closed_captioning": record.get("closed_captioning"),
        "text": text,
        "wordcount": record.get("wordcount", len(text.split())),
        "caption_empty": bool(record.get("caption_empty", not text)),
        "extra_json": json.dumps(record.get("extra", {}), ensure_ascii=False),
        "source": source,
    }


def load_rows(paths: list[Path]) -> tuple[list[dict[str, Any]], int]:
    """Read JSONL inputs in order; the first occurrence of an identifier wins."""
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    dropped = 0
    for path in paths:
        for record in iter_json_lines(path):
            if record["identifier"] in seen:
                dropped += 1
                continue
            seen.add(record["identifier"])
            rows.append(to_row(record, path.name))
    rows.sort(key=lambda r: (r["aired_date"] or date.min, r["identifier"]))
    return rows, dropped


def write_parquet(rows: list[dict[str, Any]], out: Path) -> pa.Table:
    """Write rows under :data:`SCHEMA` (zstd, 50k-row groups) and return the table."""
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out, compression="zstd", row_group_size=50_000)
    return table


def describe(table: pa.Table, dropped: int) -> str:
    """Rows per source, empties, rows per year: what to eyeball after a build."""
    lines = [
        f"rows: {table.num_rows}  duplicates dropped: {dropped}  "
        f"empty captions: {sum(table.column('caption_empty').to_pylist())}",
        "per source:",
    ]
    lines.extend(
        f"  {k}: {v}"
        for k, v in sorted(Counter(table.column("source").to_pylist()).items())
    )
    years = Counter(
        d.year if d else None for d in table.column("aired_date").to_pylist()
    )
    lines.append("per year:")
    lines.extend(
        f"  {y or 'missing'}: {n}"
        for y, n in sorted(years.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))
    )
    return "\n".join(lines)
