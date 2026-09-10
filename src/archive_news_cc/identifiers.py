"""List TV News Archive items via the Internet Archive search API.

Uses ``internetarchive.search_items``, which pages through the scrape API with
a cursor, so a query that matches millions of items streams instead of
truncating at one page. The previous implementation asked advancedsearch.php
for ``rows=N`` on page 1 and silently stopped there.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from itertools import islice
from typing import TYPE_CHECKING, Any

import internetarchive

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

from archive_news_cc.common import write_json_lines

log = logging.getLogger(__name__)

COLLECTION = "tvarchive"
FIELDS = ["identifier", "date", "publicdate", "contributor", "title"]


def build_query(
    start_date: date | None = None,
    end_date: date | None = None,
    since: date | None = None,
    contributor: str | None = None,
) -> str:
    """Compose the Lucene-style query for the TV News Archive collection.

    Args:
        start_date: First air date to include.
        end_date: Last air date to include.
        since: Only items published to archive.org on or after this date. Use
            this for incremental runs; air date can predate publication by days.
        contributor: Station code such as ``CNNW`` or ``KGO``.

    Returns:
        The query string.

    Raises:
        ValueError: If ``start_date`` is after ``end_date``.
    """
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    parts = [f"collection:{COLLECTION}"]
    if start_date or end_date:
        lower = start_date.isoformat() if start_date else "*"
        upper = end_date.isoformat() if end_date else "*"
        parts.append(f"date:[{lower} TO {upper}]")
    if since:
        parts.append(f"publicdate:[{since.isoformat()} TO *]")
    if contributor:
        parts.append(f'contributor:"{contributor}"')
    return " AND ".join(parts)


def search(query: str, sorts: list[str] | None = None) -> Iterable[dict[str, Any]]:
    """Return an iterable of result dicts for ``query`` (lazy, cursor-paged)."""
    return internetarchive.search_items(
        query, fields=FIELDS, sorts=sorts or ["publicdate desc"]
    )


def to_records(
    results: Iterable[dict[str, Any]], query: str, limit: int | None = None
) -> Iterator[dict[str, Any]]:
    """Attach rank, query and fetch time to raw search hits."""
    fetched_at = datetime.now(UTC).isoformat()
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    selected = islice(results, limit) if limit is not None else results
    for rank, hit in enumerate(selected, start=1):
        yield {**hit, "rank": rank, "query": query, "fetched_at": fetched_at}


def write_identifiers(
    output: Path,
    query: str,
    limit: int | None = None,
    results: Iterable[dict[str, Any]] | None = None,
) -> int:
    """Run ``query`` and write identifier records to ``output`` as JSONL.

    Args:
        output: Destination JSONL file (overwritten; identifier lists are
            immutable snapshots of a query at a time).
        query: From :func:`build_query`.
        limit: Stop after this many hits.
        results: Injected hits for tests; the live search otherwise.

    Returns:
        Number of records written.
    """
    log.info("query: %s", query)
    hits = results if results is not None else search(query)
    count = write_json_lines(output, to_records(hits, query, limit))
    log.info("wrote %d identifiers to %s", count, output)
    return count
