"""Download each item's metadata JSON and its /details/ page.

Why the details page: the caption files an item lists (``*.cc5.txt``,
``*.align.srt``, ``*.json``) are access-restricted and return 403 or empty
bodies for every TV News Archive item. The HTML details page is the only public
surface that carries the caption text, as ``div.snipin.nosel`` snippets.

Downloads are written to ``<name>.part`` and renamed on success, so a killed
run never leaves a truncated file that a later run would mistake for done.
"""

from __future__ import annotations

import gzip
import json
import logging
import re
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import internetarchive
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from archive_news_cc import USER_AGENT
from archive_news_cc.common import DEFAULT_DATA_DIR, iter_json_lines

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

log = logging.getLogger(__name__)

DETAILS_URL = "https://archive.org/details/{identifier}"
DEFAULT_META_DIR = DEFAULT_DATA_DIR / "meta"
DEFAULT_HTML_DIR = DEFAULT_DATA_DIR / "html"


@dataclass(slots=True)
class FetchSummary:
    """Counts reported at the end of a run."""

    requested: int = 0
    fetched: int = 0
    skipped: int = 0
    failed: list[dict[str, str]] = field(default_factory=list)


def make_session(timeout: float = 60.0, retries: int = 3) -> requests.Session:
    """A requests session with a polite user agent and 429/5xx retries."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    retry = Retry(
        total=retries,
        backoff_factor=5,
        status_forcelist=(429, 500, 502, 503, 504),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.request = _with_timeout(session.request, timeout)  # type: ignore[method-assign]
    return session


def _with_timeout(request, timeout):
    def wrapped(method, url, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return request(method, url, **kwargs)

    return wrapped


def write_atomic(path: Path, payload: bytes, compress: bool) -> None:
    """Write ``payload`` to ``path`` via a ``.part`` file and rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    if compress:
        with gzip.open(part, "wb") as handle:
            handle.write(payload)
    else:
        part.write_bytes(payload)
    part.replace(path)


def target_paths(identifier: str, meta_dir: Path, html_dir: Path) -> tuple[Path, Path]:
    """Where an item's metadata JSON and details HTML live on disk."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identifier):
        raise ValueError(f"invalid archive identifier: {identifier!r}")
    return meta_dir / f"{identifier}_meta.json", html_dir / f"{identifier}.html.gz"


def fetch_metadata(identifier: str) -> dict[str, Any]:
    """Return the item's metadata record from the archive.org metadata API."""
    item = internetarchive.get_item(identifier, request_kwargs={"timeout": 60})
    if not item.metadata:
        raise LookupError(f"no metadata for {identifier}")
    return {"metadata": item.metadata, "files": [f["name"] for f in item.files]}


def fetch_details_html(session: requests.Session, identifier: str) -> bytes:
    """Return the raw /details/ page for ``identifier``."""
    response = session.get(DETAILS_URL.format(identifier=identifier))
    response.raise_for_status()
    return response.content


def fetch_one(
    identifier: str,
    session: requests.Session,
    meta_dir: Path,
    html_dir: Path,
    refresh: bool = False,
) -> bool:
    """Fetch metadata and details HTML for one item unless both exist.

    Returns:
        ``True`` if anything was downloaded, ``False`` if both files existed.
    """
    meta_path, html_path = target_paths(identifier, meta_dir, html_dir)
    did_work = False
    if refresh or not meta_path.exists():
        payload = json.dumps(fetch_metadata(identifier), ensure_ascii=False)
        write_atomic(meta_path, payload.encode("utf-8"), compress=False)
        did_work = True
    if refresh or not html_path.exists():
        write_atomic(html_path, fetch_details_html(session, identifier), compress=True)
        did_work = True
    return did_work


def fetch_all(
    identifiers: Iterable[str],
    meta_dir: Path = DEFAULT_META_DIR,
    html_dir: Path = DEFAULT_HTML_DIR,
    *,
    max_workers: int = 2,
    min_interval: float = 1.0,
    failures_path: Path | None = None,
    session: requests.Session | None = None,
    refresh: bool = False,
) -> FetchSummary:
    """Fetch every identifier, recording failures instead of stopping.

    Args:
        identifiers: Item identifiers.
        meta_dir: Directory for ``<id>_meta.json``.
        html_dir: Directory for ``<id>.html.gz``.
        max_workers: Concurrent downloads. archive.org asks for restraint; 2 is
            the default the corpus was built with.
        min_interval: Seconds between request starts per worker.
        failures_path: JSONL of ``{identifier, error, at}`` for re-runs.
        session: Injected HTTP session for tests.
        refresh: Replace cached metadata and HTML atomically.

    Returns:
        Counts plus the list of failures.
    """
    if max_workers < 1 or min_interval < 0:
        raise ValueError("workers must be positive and interval nonnegative")
    local = threading.local()
    summary = FetchSummary()
    failures_path = failures_path or (meta_dir.parent / "fetch_failures.jsonl")

    def worker(identifier: str) -> tuple[str, bool]:
        if not hasattr(local, "session"):
            local.session = session or make_session()
        time.sleep(min_interval)
        return identifier, fetch_one(
            identifier, local.session, meta_dir, html_dir, refresh
        )

    # Keep only a bounded number of futures alive for multi-million-item searches.
    remaining = iter(dict.fromkeys(identifiers))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        pending = {}
        exhausted = False
        while pending or not exhausted:
            while len(pending) < max_workers * 2 and not exhausted:
                try:
                    identifier = next(remaining)
                except StopIteration:
                    exhausted = True
                    break
                pending[pool.submit(worker, identifier)] = identifier
                summary.requested += 1
            if not pending:
                break
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                identifier = pending.pop(future)
                try:
                    _, did_work = future.result()
                except Exception as exc:
                    log.warning("failed %s: %s", identifier, exc)
                    failure = {
                        "identifier": identifier,
                        "error": f"{type(exc).__name__}: {exc}",
                        "at": datetime.now(UTC).isoformat(),
                    }
                    summary.failed.append(failure)
                    failures_path.parent.mkdir(parents=True, exist_ok=True)
                    with failures_path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(failure) + "\n")
                        handle.flush()
                    continue
                if did_work:
                    summary.fetched += 1
                else:
                    summary.skipped += 1
    log.info(
        "done: %d requested, %d fetched, %d skipped, %d failed",
        summary.requested,
        summary.fetched,
        summary.skipped,
        len(summary.failed),
    )
    return summary


def identifiers_from_records(path: Path) -> list[str]:
    """Read the ``identifier`` field from an identifiers JSONL file."""
    return [str(row["identifier"]) for row in iter_json_lines(path)]
