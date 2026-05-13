from __future__ import annotations

import argparse
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from bs4 import BeautifulSoup

from archive_news_cc.common import (
    DEFAULT_HTML_DIR,
    DEFAULT_META_DIR,
    add_logging_arguments,
    configure_logging,
    iter_identifier_rows,
    iter_json_lines,
    open_maybe_gzip,
    resolve_existing,
    write_json_lines,
)


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description="Parse Archive.org metadata and HTML into JSON Lines."
        )
    parser.add_argument(
        "input_records", type=Path, help="JSONL file containing identifier records."
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=Path,
        default=Path("archive-out.jsonl.gz"),
        help="Output JSONL or JSONL.GZ filename.",
    )
    parser.add_argument(
        "--meta",
        type=Path,
        default=DEFAULT_META_DIR,
        help="Metadata files directory.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML_DIR,
        help="HTML files directory.",
    )
    parser.add_argument(
        "-s",
        "--skip",
        type=int,
        default=0,
        help="Skip records from the input JSONL.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip identifiers already present in the output file and append new records.",
    )
    add_logging_arguments(parser)
    return parser


def normalize_values(values: list[str]) -> str | list[str]:
    if len(values) == 1:
        return values[0]
    return values


def parse_meta_file(meta_path: Path) -> dict[str, str | list[str]]:
    with open_maybe_gzip(meta_path, "rb") as handle:
        root = ET.fromstring(handle.read())

    parsed: dict[str, list[str]] = {}
    for element in root.iter():
        text = (element.text or "").strip()
        if not text:
            continue
        parsed.setdefault(element.tag, []).append(text)

    return {key: normalize_values(values) for key, values in parsed.items()}


def parse_html_file(html_path: Path) -> str:
    with open_maybe_gzip(html_path, "rb") as handle:
        soup = BeautifulSoup(handle.read(), "html.parser")
    snippets = [
        node.get_text(strip=True)
        for node in soup.find_all("div", {"class": "snipin nosel"})
    ]
    return "".join(snippets)


def build_rows(
    input_records: Path,
    meta_dir: Path,
    html_dir: Path,
    skip: int,
    existing_identifiers: set[str] | None = None,
):
    processed = 0
    emitted = 0
    for index, row in enumerate(iter_identifier_rows(input_records, skip=skip), start=1):
        identifier = str(row["identifier"])
        if existing_identifiers and identifier in existing_identifiers:
            logging.info("Skipping already parsed identifier %s", identifier)
            continue

        processed += 1
        logging.info("Parsing #%s: %s", index, identifier)
        meta_path = resolve_existing(meta_dir / f"{identifier}_meta.xml")
        html_path = resolve_existing(html_dir / f"{identifier}.html")
        if not meta_path or not html_path:
            logging.warning("Skipping %s because metadata or HTML is missing", identifier)
            continue

        try:
            parsed = {
                "identifier": identifier,
                "identifier_record": row,
                "source": {
                    "meta_path": str(meta_path),
                    "html_path": str(html_path),
                },
                "metadata": parse_meta_file(meta_path),
                "transcript": {
                    "text": parse_html_file(html_path),
                },
            }
        except Exception as exc:
            logging.warning("Skipping %s because parsing failed: %s", identifier, exc)
            continue
        emitted += 1
        yield parsed
    logging.info("Processed %s new identifiers and emitted %s records", processed, emitted)


def read_existing_identifiers(path: Path) -> set[str]:
    if not path.exists():
        return set()
    identifiers = {
        str(record["identifier"])
        for record in iter_json_lines(path)
        if "identifier" in record
    }
    logging.info("Found %s existing parsed identifiers in %s", len(identifiers), path)
    return identifiers


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


def run(args: argparse.Namespace) -> int:
    configure_logging(
        "parse_archive.log",
        log_level=args.log_level,
        log_dir=args.log_dir,
    )
    existing_identifiers = read_existing_identifiers(args.outfile) if args.resume else set()
    rows = build_rows(
        args.input_records,
        args.meta,
        args.html,
        args.skip,
        existing_identifiers,
    )
    write_json_lines(args.outfile, rows, mode="at" if args.resume else "wt")
    logging.info("Wrote parsed output to %s", args.outfile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
