"""``archive-news-cc identifiers | fetch | parse | to-parquet | upload``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from archive_news_cc import convert, fetch, identifiers, parse, upload
from archive_news_cc.common import DEFAULT_DATA_DIR, configure_logging, write_json_lines

log = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="archive-news-cc")
    parser.add_argument(
        "--log", type=Path, default=DEFAULT_DATA_DIR / "archive_news_cc.log"
    )
    parser.add_argument("--log-level", default="INFO")
    sub = parser.add_subparsers(dest="command", required=True)

    i = sub.add_parser("identifiers", help="write a JSONL list of matching items")
    i.add_argument("--out", type=Path, default=DEFAULT_DATA_DIR / "identifiers.jsonl")
    i.add_argument("--start-date", type=date.fromisoformat, help="first air date")
    i.add_argument("--end-date", type=date.fromisoformat, help="last air date")
    i.add_argument("--since", type=date.fromisoformat, help="published on/after")
    i.add_argument("--contributor", help="station code, e.g. CNNW")
    i.add_argument("--limit", type=int, help="stop after N items")

    f = sub.add_parser("fetch", help="download metadata JSON and details HTML")
    f.add_argument("records", type=Path, help="identifiers JSONL")
    f.add_argument("--meta", type=Path, default=fetch.DEFAULT_META_DIR)
    f.add_argument("--html", type=Path, default=fetch.DEFAULT_HTML_DIR)
    f.add_argument("--refresh", action="store_true", help="replace cached downloads")
    f.add_argument("--max-workers", type=int, default=2)
    f.add_argument("--min-interval", type=float, default=1.0, help="seconds/request")

    p = sub.add_parser("parse", help="parse fetched files into JSONL records")
    p.add_argument("records", type=Path, help="identifiers JSONL")
    p.add_argument("--out", type=Path, default=DEFAULT_DATA_DIR / "captions.jsonl")
    p.add_argument("--meta", type=Path, default=fetch.DEFAULT_META_DIR)
    p.add_argument("--html", type=Path, default=fetch.DEFAULT_HTML_DIR)
    p.add_argument("--resume", action="store_true", help="append; skip ids already out")

    c = sub.add_parser("to-parquet", help="combine parsed JSONL into one Parquet")
    c.add_argument("inputs", type=Path, nargs="+")
    c.add_argument("--out", type=Path, required=True)

    u = sub.add_parser("upload", help="add a file to the Dataverse dataset")
    u.add_argument("file", type=Path)
    u.add_argument("--doi", default=upload.DATASET_DOI)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return an exit status (1 when any item failed)."""
    args = _build_parser().parse_args(argv)
    configure_logging(args.log, args.log_level)

    if args.command == "identifiers":
        query = identifiers.build_query(
            args.start_date, args.end_date, args.since, args.contributor
        )
        identifiers.write_identifiers(args.out, query, args.limit)
        return 0
    if args.command == "fetch":
        ids = fetch.identifiers_from_records(args.records)
        summary = fetch.fetch_all(
            ids,
            args.meta,
            args.html,
            max_workers=args.max_workers,
            min_interval=args.min_interval,
            refresh=args.refresh,
        )
        return 1 if summary.failed else 0
    if args.command == "parse":
        ids = fetch.identifiers_from_records(args.records)
        skip = parse.existing_identifiers(args.out) if args.resume else set()
        summary = parse.ParseSummary()
        rows = parse.parse_all(ids, args.meta, args.html, skip, summary)
        write_json_lines(args.out, rows, mode="at" if args.resume else "wt")
        log.info(
            "parsed %d of %d (skipped %d, missing files %d, empty captions %d)",
            summary.emitted,
            summary.seen,
            summary.skipped_existing,
            len(summary.missing_files),
            summary.empty_captions,
        )
        for identifier in summary.missing_files:
            log.warning("missing files: %s", identifier)
        return 1 if summary.missing_files else 0
    if args.command == "to-parquet":
        rows, dropped = convert.load_rows(args.inputs)
        table = convert.write_parquet(rows, args.out)
        sys.stdout.write(convert.describe(table, dropped) + "\n")
        return 0
    if args.command == "upload":
        sys.stdout.write(upload.upload(args.file, args.doi) + "\n")
        return 0
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
