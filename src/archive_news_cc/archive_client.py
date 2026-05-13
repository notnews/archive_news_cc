from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

import requests

from archive_news_cc.common import ensure_parent_dir

DEFAULT_USER_AGENT = "archive-news-cc/0.1.0 (+https://github.com/notnews/archive_news_cc)"


def add_archive_http_arguments(parser) -> None:
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--min-request-interval",
        type=float,
        default=1.0,
        help="Minimum delay between Archive.org HTTP requests across the process.",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header sent to Archive.org.",
    )


class ArchiveClient:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        request_timeout: float = 60.0,
        min_request_interval: float = 1.0,
    ) -> None:
        self.request_timeout = request_timeout
        self.min_request_interval = min_request_interval
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})
        self._lock = threading.Lock()
        self._last_request_monotonic = 0.0

    def _wait_for_turn(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_time = self.min_request_interval - (now - self._last_request_monotonic)
            if wait_time > 0:
                logging.debug("Sleeping %.2fs to respect request interval", wait_time)
                time.sleep(wait_time)
            self._last_request_monotonic = time.monotonic()

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        self._wait_for_turn()
        response = self._session.request(
            method,
            url,
            timeout=self.request_timeout,
            **kwargs,
        )
        return response

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def get_with_backoff(
        self,
        url: str,
        *,
        retries: int,
        backoff_seconds: float,
        **kwargs,
    ) -> requests.Response:
        for attempt in range(1, retries + 1):
            response = self.get(url, **kwargs)
            if response.status_code not in {429, 503}:
                response.raise_for_status()
                return response

            retry_after = response.headers.get("Retry-After")
            wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else backoff_seconds * attempt
            if attempt == retries:
                response.raise_for_status()
            logging.warning(
                "Archive.org responded with %s for %s; retrying in %.1fs (%s/%s)",
                response.status_code,
                url,
                wait_seconds,
                attempt,
                retries,
            )
            time.sleep(wait_seconds)

        raise RuntimeError(f"Failed to retrieve {url}")

    def stream_to_file(
        self,
        url: str,
        output_path: Path,
        *,
        retries: int,
        backoff_seconds: float,
    ) -> None:
        ensure_parent_dir(output_path)
        response = self.get_with_backoff(
            url,
            retries=retries,
            backoff_seconds=backoff_seconds,
            stream=True,
        )
        with output_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if chunk:
                    handle.write(chunk)
