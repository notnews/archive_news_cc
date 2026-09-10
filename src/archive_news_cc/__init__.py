"""Closed captions of TV news from the Internet Archive's TV News Archive."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("archive-news-cc")
except PackageNotFoundError:  # pragma: no cover - not installed
    __version__ = "0.0.0"

USER_AGENT = (
    f"archive-news-cc/{__version__} (+https://github.com/notnews/archive_news_cc)"
)
