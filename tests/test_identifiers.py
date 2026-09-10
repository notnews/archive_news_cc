import json
from datetime import date

import pytest

from archive_news_cc import identifiers


def test_build_query_variants():
    assert identifiers.build_query() == "collection:tvarchive"
    assert (
        identifiers.build_query(date(2026, 1, 1), date(2026, 1, 31))
        == "collection:tvarchive AND date:[2026-01-01 TO 2026-01-31]"
    )
    assert "publicdate:[2026-09-09 TO *]" in identifiers.build_query(
        since=date(2026, 9, 9)
    )
    assert 'contributor:"CNNW"' in identifiers.build_query(contributor="CNNW")
    with pytest.raises(ValueError, match="start_date"):
        identifiers.build_query(date(2026, 2, 1), date(2026, 1, 1))


def test_write_identifiers_ranks_and_limits(tmp_path):
    hits = ({"identifier": f"ID{i}", "date": "2026-09-09T00:00:00Z"} for i in range(10))
    out = tmp_path / "ids.jsonl"
    n = identifiers.write_identifiers(out, "q", limit=3, results=hits)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert n == 3
    assert [r["identifier"] for r in rows] == ["ID0", "ID1", "ID2"]
    assert [r["rank"] for r in rows] == [1, 2, 3]
    assert rows[0]["query"] == "q"
    assert rows[0]["fetched_at"].endswith("+00:00")
