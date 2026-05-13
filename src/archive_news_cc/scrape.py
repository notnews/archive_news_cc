from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import logging
import os
import time
from pathlib import Path

from archive_news_cc.archive_client import ArchiveClient, add_archive_http_arguments
from archive_news_cc.common import (
    DEFAULT_HTML_DIR,
    DEFAULT_META_DIR,
    add_logging_arguments,
    configure_logging,
    read_identifiers,
)

ARCHIVE_DOWNLOAD_BASE = "https://archive.org/download"
ARCHIVE_DETAILS_BASE = "https://archive.org/details"
MAX_RETRIES = 5


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description="Download Archive.org metadata and HTML files."
        )
    parser.add_argument(
        "input_records", type=Path, help="JSONL file containing identifier records."
    )
    parser.add_argument(
        "--meta",
        type=Path,
        default=DEFAULT_META_DIR,
        help="Metadata output directory.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML_DIR,
        help="HTML output directory.",
    )
    parser.add_argument(
        "-s",
        "--skip",
        type=int,
        default=0,
        help="Skip records from the input JSONL.",
    )
    parser.add_argument(
        "-c",
        "--compress",
        action="store_true",
        help="Store downloaded files as gzip.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=int(os.environ.get("MAX_WORKERS", 2)),
        help="Maximum concurrent downloads.",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=15.0,
        help="Base backoff in seconds after 429/503 or transient failures.",
    )
    add_archive_http_arguments(parser)
    add_logging_arguments(parser)
    return parser


def destination_path(directory: Path, filename: str, compress: bool) -> Path:
    path = directory / filename
    if compress:
        return Path(f"{path}.gz")
    return path


def download_file(
    client: ArchiveClient,
    url: str,
    output_path: Path,
    compress: bool,
    retry_backoff: float,
) -> None:
    logging.info("Downloading %s", url)
    response = client.get_with_backoff(
        url,
        retries=MAX_RETRIES,
        backoff_seconds=retry_backoff,
        stream=True,
    )

    if compress:
        with gzip.open(output_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    handle.write(chunk)
    else:
        with output_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    handle.write(chunk)


def download_identifier(
    client: ArchiveClient,
    identifier: str,
    meta_dir: Path,
    html_dir: Path,
    compress: bool,
    retry_backoff: float,
) -> None:
    meta_path = destination_path(meta_dir, f"{identifier}_meta.xml", compress)
    html_path = destination_path(html_dir, f"{identifier}.html", compress)

    if not meta_path.exists():
        download_file(
            client,
            f"{ARCHIVE_DOWNLOAD_BASE}/{identifier}/{identifier}_meta.xml",
            meta_path,
            compress,
            retry_backoff,
        )

    if not html_path.exists():
        download_file(
            client,
            f"{ARCHIVE_DETAILS_BASE}/{identifier}",
            html_path,
            compress,
            retry_backoff,
        )


def download_with_retry(
    client: ArchiveClient,
    identifier: str,
    meta_dir: Path,
    html_dir: Path,
    compress: bool,
    retry_backoff: float,
) -> None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            download_identifier(
                client,
                identifier,
                meta_dir,
                html_dir,
                compress,
                retry_backoff,
            )
            return
        except Exception as exc:
            if attempt == MAX_RETRIES:
                logging.error("id=%s failed after retries: %s", identifier, exc)
                raise
            logging.warning(
                "id=%s failed on attempt %s/%s; retrying in %.1fs",
                identifier,
                attempt,
                MAX_RETRIES,
                retry_backoff * attempt,
            )
            time.sleep(retry_backoff * attempt)


def run_downloads(
    client: ArchiveClient,
    identifiers: list[str],
    meta_dir: Path,
    html_dir: Path,
    compress: bool,
    max_workers: int,
    test_mode: bool,
    retry_backoff: float,
) -> None:
    meta_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)

    if test_mode:
        for identifier in identifiers:
            download_with_retry(
                client, identifier, meta_dir, html_dir, compress, retry_backoff
            )
        return

    logging.info("%s total identifiers to process", len(identifiers))
    logging.info(
        "Using max_workers=%s and min_request_interval=%.2fs",
        max_workers,
        client.min_request_interval,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                download_with_retry,
                client,
                identifier,
                meta_dir,
                html_dir,
                compress,
                retry_backoff,
            )
            for identifier in identifiers
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()


def run(args: argparse.Namespace) -> int:
    configure_logging(
        "scrape_archive_org.log",
        log_level=args.log_level,
        log_dir=args.log_dir,
    )
    logging.info("Max workers set to %s", args.max_workers)
    client = ArchiveClient(
        user_agent=args.user_agent,
        request_timeout=args.request_timeout,
        min_request_interval=args.min_request_interval,
    )
    identifiers = read_identifiers(args.input_records, skip=args.skip)
    run_downloads(
        client=client,
        identifiers=identifiers,
        meta_dir=args.meta,
        html_dir=args.html,
        compress=args.compress,
        max_workers=args.max_workers,
        test_mode=bool(os.environ.get("ARCHIVE_TEST")),
        retry_backoff=args.retry_backoff,
    )
    logging.info("All done")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
