import gzip
import json
import shutil

from archive_news_cc import parse


def test_parse_captions_joins_snippets_with_spaces(fixture_path):
    text = parse.parse_captions(fixture_path("details_captions.html").read_bytes())
    assert text.startswith(">> season premiere. halloween baking championship.")
    assert "cupertino on wednesday. the new phone duo" in text
    # snippet boundary must not glue two words together
    assert "right now. >> live from los angeles" in text
    assert len(text.split()) > 300


def test_parse_captions_empty_placeholders(fixture_path):
    assert (
        parse.parse_captions(fixture_path("details_no_captions.html").read_bytes())
        == ""
    )


def test_parse_captions_tolerates_double_space_class():
    html = (
        '<div class="snipin  nosel" unselectable="on">a b</div>'
        '<div class="snipin">x</div>'
    )
    assert parse.parse_captions(html) == "a b"


def test_parse_metadata_promotes_and_flattens(fixture_path):
    record = json.loads(fixture_path("meta_item.json").read_text())
    meta = parse.parse_metadata(record)
    assert meta["contributor"] == "KGO"
    assert meta["date"] == "2026-09-10"
    assert meta["access_restricted_item"] == "true"
    assert isinstance(meta["extra"]["collection"], list)  # untouched in extra
    assert "title" not in meta["extra"]
    assert any(name.endswith("_meta.xml") for name in meta["files"])
    assert not any(".thumbs/" in name for name in meta["files"])


def test_parse_all_counts_missing_skipped_and_empty(fixture_path, tmp_path):
    meta_dir, html_dir = tmp_path / "meta", tmp_path / "html"
    meta_dir.mkdir()
    html_dir.mkdir()
    for ident, page in [
        ("A", "details_captions.html"),
        ("B", "details_no_captions.html"),
    ]:
        shutil.copy(fixture_path("meta_item.json"), meta_dir / f"{ident}_meta.json")
        with gzip.open(html_dir / f"{ident}.html.gz", "wb") as handle:
            handle.write(fixture_path(page).read_bytes())
    summary = parse.ParseSummary()
    rows = list(
        parse.parse_all(["A", "B", "C", "D"], meta_dir, html_dir, {"D"}, summary)
    )
    assert [r["identifier"] for r in rows] == ["A", "B"]
    assert rows[0]["caption_empty"] is False
    assert rows[1]["caption_empty"] is True
    assert rows[1]["wordcount"] == 0
    assert summary.seen == 4
    assert summary.missing_files == ["C"]
    assert summary.skipped_existing == 1
    assert summary.empty_captions == 1
