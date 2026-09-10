"""Turn fetched metadata JSON and details HTML into one record per item."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup

from archive_news_cc.checkpoint import prepare_checkpoint
from archive_news_cc.common import iter_json_lines, open_maybe_gzip, resolve_existing
from archive_news_cc.fetch import DEFAULT_HTML_DIR, DEFAULT_META_DIR

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

log = logging.getLogger(__name__)

# Metadata keys promoted to top-level columns. Everything else stays in `extra`.
PROMOTED = (
    "title",
    "date",
    "publicdate",
    "contributor",
    "description",
    "language",
    "runtime",
    "closed_captioning",
    "access-restricted-item",
)


@dataclass(slots=True)
class ParseSummary:
    """Counts reported at the end of a run."""

    seen: int = 0
    emitted: int = 0
    skipped_existing: int = 0
    missing_files: list[str] = field(default_factory=list)
    empty_captions: int = 0


def parse_captions(html: str | bytes) -> str:
    """Return the caption text of a details page.

    Snippets sit in ``div.snipin.nosel`` elements. The class attribute has
    carried a double space (``"snipin  nosel"``) in captured pages. CSS selectors match
    each class token. Snippets are
    joined with a space so sentence boundaries survive.
    """
    soup = BeautifulSoup(html, "html.parser")
    parts = (div.get_text(" ", strip=True) for div in soup.select("div.snipin.nosel"))
    return " ".join(p for p in parts if p)


def _scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return "; ".join(str(v) for v in value) if value else None
    return str(value)


def parse_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten a saved metadata record into promoted columns plus ``extra``."""
    meta = record.get("metadata", record)
    promoted = {key.replace("-", "_"): _scalar(meta.get(key)) for key in PROMOTED}
    extra = {k: v for k, v in meta.items() if k not in PROMOTED}
    return {**promoted, "files": record.get("files", []), "extra": extra}


def parse_item(identifier: str, meta_path: Path, html_path: Path) -> dict[str, Any]:
    """Build the record for one item from its two files on disk."""
    with open_maybe_gzip(meta_path, "rt") as handle:
        meta = parse_metadata(json.load(handle))
    with open_maybe_gzip(html_path, "rb") as handle:
        text = parse_captions(handle.read())
    return {
        "identifier": identifier,
        **meta,
        "text": text,
        "wordcount": len(text.split()),
        "caption_empty": not text,
        "source": {"meta_path": str(meta_path), "html_path": str(html_path)},
    }


def existing_identifiers(path: Path) -> set[str]:
    """Identifiers already present in an output JSONL, for ``--resume``."""
    if not path.exists():
        return set()
    prepare_checkpoint(path)
    return {str(r["identifier"]) for r in iter_json_lines(path) if "identifier" in r}


def parse_all(
    identifiers: list[str],
    meta_dir: Path = DEFAULT_META_DIR,
    html_dir: Path = DEFAULT_HTML_DIR,
    skip: set[str] | None = None,
    summary: ParseSummary | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield a record per identifier whose files exist; count the rest."""
    summary = summary if summary is not None else ParseSummary()
    skip = skip or set()
    for identifier in identifiers:
        summary.seen += 1
        if identifier in skip:
            summary.skipped_existing += 1
            continue
        meta_path = resolve_existing(meta_dir / f"{identifier}_meta.json")
        html_path = resolve_existing(html_dir / f"{identifier}.html")
        if meta_path is None or html_path is None:
            summary.missing_files.append(identifier)
            continue
        record = parse_item(identifier, meta_path, html_path)
        if record["caption_empty"]:
            summary.empty_captions += 1
        summary.emitted += 1
        skip.add(identifier)
        yield record
