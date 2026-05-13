from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path
from typing import Iterable, Iterator


DEFAULT_DATA_DIR = Path("data")
DEFAULT_META_DIR = DEFAULT_DATA_DIR / "meta"
DEFAULT_HTML_DIR = DEFAULT_DATA_DIR / "html"
DEFAULT_LOG_DIR = Path("logs")


def add_logging_arguments(parser) -> None:
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help="Directory for log files.",
    )


def configure_logging(log_name: str, *, log_level: str = "INFO", log_dir: Path = DEFAULT_LOG_DIR) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / log_name),
            logging.StreamHandler(),
        ],
        force=True,
    )


def open_maybe_gzip(path: Path, mode: str):
    if path.suffix == ".gz":
        return gzip.open(path, mode)
    return path.open(mode)


def resolve_existing(base_path: Path) -> Path | None:
    if base_path.is_file():
        return base_path

    gz_path = Path(f"{base_path}.gz")
    if gz_path.is_file():
        return gz_path
    return None


def read_identifier_records(path: Path, skip: int = 0) -> list[dict[str, object]]:
    with open_maybe_gzip(path, "rt") as handle:
        return [
            json.loads(line)
            for index, line in enumerate(handle)
            if line.strip() and index >= skip
        ]


def read_identifiers(path: Path, skip: int = 0) -> list[str]:
    return [str(record["identifier"]) for record in read_identifier_records(path, skip)]


def iter_identifier_rows(path: Path, skip: int = 0) -> Iterator[dict[str, object]]:
    with open_maybe_gzip(path, "rt") as handle:
        for index, line in enumerate(handle):
            if not line.strip() or index < skip:
                continue
            yield json.loads(line)


def iter_json_lines(path: Path) -> Iterator[dict[str, object]]:
    with open_maybe_gzip(path, "rt") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json_lines(
    output_path: Path,
    rows: Iterable[dict[str, object]],
    *,
    mode: str = "wt",
) -> None:
    ensure_parent_dir(output_path)
    with open_maybe_gzip(output_path, mode) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True))
            handle.write("\n")


def write_json(path: Path, data: dict[str, object]) -> None:
    ensure_parent_dir(path)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
