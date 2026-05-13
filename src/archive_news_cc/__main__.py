from archive_news_cc.identifiers import build_parser as build_identifiers_parser
from archive_news_cc.identifiers import run as identifiers_run
from archive_news_cc.parse import build_parser as build_parse_parser
from archive_news_cc.parse import run as parse_run
from archive_news_cc.scrape import build_parser as build_scrape_parser
from archive_news_cc.scrape import run as scrape_run


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="archive-news-cc",
        description="Archive.org TV news closed-caption utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    identifiers_parser = subparsers.add_parser(
        "identifiers", help="Fetch show identifiers."
    )
    build_identifiers_parser(identifiers_parser)
    identifiers_parser.set_defaults(handler=identifiers_run)

    scrape_parser = subparsers.add_parser(
        "scrape", help="Download metadata and HTML files."
    )
    build_scrape_parser(scrape_parser)
    scrape_parser.set_defaults(handler=scrape_run)

    parse_parser = subparsers.add_parser(
        "parse", help="Parse metadata and HTML into a CSV."
    )
    build_parse_parser(parse_parser)
    parse_parser.set_defaults(handler=parse_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
