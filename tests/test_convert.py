import json
from datetime import date

import pyarrow.parquet as pq

from archive_news_cc import convert


def test_jsonl_to_parquet_dedupes_sorts_and_types(tmp_path):
    rows = [
        {
            "identifier": "B",
            "title": "b",
            "date": "2026-09-10",
            "contributor": "KGO",
            "text": "",
            "wordcount": 0,
            "caption_empty": True,
            "extra": {"k": [1, 2]},
        },
        {
            "identifier": "A",
            "title": "a",
            "date": "2026-09-09T00:00:00Z",
            "contributor": "CNNW",
            "text": "one two three",
            "wordcount": 3,
            "caption_empty": False,
            "extra": {},
        },
        {"identifier": "A", "title": "dup", "date": None, "text": "x"},
    ]
    src = tmp_path / "captions.jsonl"
    src.write_text("".join(json.dumps(r) + "\n" for r in rows))
    loaded, dropped = convert.load_rows([src])
    assert dropped == 1
    assert [r["identifier"] for r in loaded] == ["A", "B"]  # sorted by aired_date

    out = tmp_path / "out.parquet"
    convert.write_parquet(loaded, out)
    back = pq.read_table(out)
    assert back.schema.equals(convert.SCHEMA)
    a, b = back.to_pylist()
    assert a["aired_date"] == date(2026, 9, 9)
    assert a["wordcount"] == 3
    assert a["caption_empty"] is False
    assert b["caption_empty"] is True
    assert json.loads(b["extra_json"]) == {"k": [1, 2]}
    text = convert.describe(back, dropped)
    assert "rows: 2" in text
    assert "empty captions: 1" in text
    assert "2026: 2" in text
