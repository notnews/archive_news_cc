import json

import pytest

from archive_news_cc.checkpoint import prepare_checkpoint


@pytest.mark.parametrize("tail", [b'{"id":', b'{"text":"\xe2\x82'])
def test_interrupted_tail_keeps_completed_rows(tmp_path, tail):
    path = tmp_path / "checkpoint.jsonl"
    complete = b'{"id":"saved"}\n'
    path.write_bytes(complete + tail)
    prepare_checkpoint(path)
    assert path.read_bytes() == complete
    with path.open("a") as handle:
        handle.write('{"id":"next"}\n')
    assert [json.loads(line)["id"] for line in path.read_text().splitlines()] == [
        "saved",
        "next",
    ]


def test_valid_unterminated_record_is_kept(tmp_path):
    path = tmp_path / "checkpoint.jsonl"
    path.write_text('{"id":"saved"}')
    prepare_checkpoint(path)
    assert path.read_text() == '{"id":"saved"}\n'
    prepare_checkpoint(path)
    assert path.read_text() == '{"id":"saved"}\n'
