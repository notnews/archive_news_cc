import gzip
import json

from archive_news_cc import fetch


class FakeResponse:
    def __init__(self, content=b"<html>ok</html>", status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise OSError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, fail_for=()):
        self.fail_for = set(fail_for)
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        ident = url.rsplit("/", 1)[-1]
        if ident in self.fail_for:
            return FakeResponse(status=403)
        return FakeResponse(f"<html>{ident}</html>".encode())


def test_write_atomic_leaves_no_part_file(tmp_path):
    target = tmp_path / "x" / "a.html.gz"
    fetch.write_atomic(target, b"hello", compress=True)
    assert gzip.decompress(target.read_bytes()) == b"hello"
    assert not list(tmp_path.glob("**/*.part"))


def test_fetch_all_records_failures_and_skips_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        fetch, "fetch_metadata", lambda i: {"metadata": {"title": i}, "files": []}
    )
    meta_dir, html_dir = tmp_path / "meta", tmp_path / "html"
    session = FakeSession(fail_for={"BAD"})
    summary = fetch.fetch_all(
        ["OK1", "BAD", "OK2"],
        meta_dir,
        html_dir,
        max_workers=2,
        min_interval=0,
        session=session,
    )
    assert summary.requested == 3
    assert summary.fetched == 2
    assert [f["identifier"] for f in summary.failed] == ["BAD"]
    assert "HTTP 403" in summary.failed[0]["error"]
    failures = tmp_path / "fetch_failures.jsonl"
    assert json.loads(failures.read_text())["identifier"] == "BAD"
    assert (meta_dir / "OK1_meta.json").exists()
    assert (
        gzip.decompress((html_dir / "OK2.html.gz").read_bytes()) == b"<html>OK2</html>"
    )
    assert not (html_dir / "BAD.html.gz").exists()

    again = fetch.fetch_all(
        ["OK1", "OK2"], meta_dir, html_dir, min_interval=0, session=FakeSession()
    )
    assert (again.fetched, again.skipped) == (0, 2)


def test_refresh_and_duplicate_identifiers(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "fetch_metadata", lambda i: {"metadata": {"title": i}})
    session = FakeSession()
    meta, html = tmp_path / "meta", tmp_path / "html"
    first = fetch.fetch_all(["ONE", "ONE"], meta, html, min_interval=0, session=session)
    assert first.requested == 1
    assert first.fetched == 1
    second = fetch.fetch_all(
        ["ONE"], meta, html, min_interval=0, session=session, refresh=True
    )
    assert second.fetched == 1
    assert len(session.calls) == 2
