from __future__ import annotations

import argparse
import io
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from archive_news_cc.archive_client import ArchiveClient, add_archive_http_arguments
from archive_news_cc.common import add_logging_arguments, configure_logging, write_json_lines


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description="Get TV archive identifiers from Archive.org."
        )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=25,
        help="Limit number of identifiers to fetch.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/identifiers.jsonl"),
        help="Output JSONL filename.",
    )
    parser.add_argument(
        "-sd",
        "--start-date",
        type=date.fromisoformat,
        help="Starting date filter in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "-ed",
        "--end-date",
        type=date.fromisoformat,
        help="Ending date filter in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--sort",
        default="date desc",
        help="Archive.org sort expression, for example 'date desc' or 'publicdate desc'.",
    )
    add_archive_http_arguments(parser)
    add_logging_arguments(parser)
    return parser


def build_query(start_date: date | None, end_date: date | None) -> str:
    query = 'collection:"tvarchive"'
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    if start_date or end_date:
        lower = start_date.isoformat() if start_date else "0001-01-01"
        upper = end_date.isoformat() if end_date else "null"
        query += f" AND date:[{lower} TO {upper}]"
    return query


def parse_identifier_csv(payload: bytes) -> list[str]:
    text = payload.decode("utf-8")
    rows = [line.strip().strip('"') for line in text.splitlines() if line.strip()]
    if rows and rows[0] == "identifier":
        rows = rows[1:]
    return rows


def fetch_identifiers(
    client: ArchiveClient,
    count: int,
    output_path: Path,
    start_date: date | None,
    end_date: date | None,
    sort: str,
) -> None:
    logging.info("Searching and downloading TV archive identifiers.")

    query = build_query(start_date, end_date)
    logging.info("Using Archive.org query: %s", query)

    params = {
        "q": query,
        "fl[]": "identifier",
        "sort[]": sort,
        "rows": count,
        "page": 1,
        "output": "csv",
    }

    response = client.get_with_backoff(
        "https://archive.org/advancedsearch.php",
        retries=5,
        backoff_seconds=10.0,
        params=params,
        stream=True,
    )

    payload = io.BytesIO()
    for chunk in response.iter_content(64 * 1024):
        if chunk:
            payload.write(chunk)

    fetched_at = datetime.now(timezone.utc).isoformat()
    records = [
        {
            "identifier": identifier,
            "rank": index,
            "query": query,
            "sort": sort,
            "fetched_at": fetched_at,
        }
        for index, identifier in enumerate(
            parse_identifier_csv(payload.getvalue()), start=1
        )
    ]
    write_json_lines(output_path, records)
    logging.info("Wrote %s identifiers to %s", len(records), output_path)


def run(args: argparse.Namespace) -> int:
    configure_logging(
        "get_news_identifiers.log",
        log_level=args.log_level,
        log_dir=args.log_dir,
    )
    client = ArchiveClient(
        user_agent=args.user_agent,
        request_timeout=args.request_timeout,
        min_request_interval=args.min_request_interval,
    )
    fetch_identifiers(
        client,
        args.count,
        args.output,
        args.start_date,
        args.end_date,
        args.sort,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
