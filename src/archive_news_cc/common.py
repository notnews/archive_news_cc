"""Small shared helpers: gzip-aware IO, JSONL, logging setup."""

from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

DEFAULT_DATA_DIR = Path("data")


def configure_logging(log_file: Path | None, level: str = "INFO") -> None:
    """Log to stderr and, when given, to ``log_file`` (parents created)."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )


def open_maybe_gzip(path: Path, mode: str) -> IO[Any]:
    """Open ``path`` with gzip when its suffix is ``.gz``."""
    if path.suffix == ".gz":
        return gzip.open(path, mode)  # type: ignore[return-value]
    return path.open(mode)


def resolve_existing(base_path: Path) -> Path | None:
    """Return ``base_path`` or its ``.gz`` twin, whichever exists."""
    if base_path.is_file():
        return base_path
    gz_path = Path(f"{base_path}.gz")
    return gz_path if gz_path.is_file() else None


def iter_json_lines(path: Path) -> Iterator[dict[str, Any]]:
    """Yield one dict per non-blank line of a JSONL or JSONL.gz file."""
    with open_maybe_gzip(path, "rt") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_json_lines(
    path: Path, rows: Iterable[dict[str, Any]], mode: str = "wt"
) -> int:
    """Write ``rows`` as JSONL (gzip when ``.gz``), returning the count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open_maybe_gzip(path, mode) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")
            count += 1
    return count
