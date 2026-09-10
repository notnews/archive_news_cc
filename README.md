## Closed Captions of News Videos from archive.org

[![CI](https://github.com/notnews/archive_news_cc/actions/workflows/ci.yml/badge.svg)](https://github.com/notnews/archive_news_cc/actions/workflows/ci.yml)
[![Data: Dataverse](https://img.shields.io/badge/data-10.7910%2FDVN%2FOAJJHI-blue)](https://doi.org/10.7910/DVN/OAJJHI)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)

The Internet Archive's [TV News Archive](https://archive.org/details/tvarchive) records US and international news broadcasts and shows their closed captions on each item's page. This repository holds the tools that turned about 2.5 million of those items (2009 to 2023) into a text corpus, and the record of how. The corpus itself is on Harvard Dataverse at [doi:10.7910/DVN/OAJJHI](https://doi.org/10.7910/DVN/OAJJHI). Credit the Internet Archive for the captions.

### Data

Four collection runs, each published as a CSV of parsed captions plus the raw pages and metadata it came from. Sizes are approximate; files over 2 GB are split into `*a`, `*b`, ... parts.

| Run | Items | Captions CSV | Raw HTML | Metadata |
|---|---|---|---|---|
| 2014 | 500k | `archive-cc-2014.csv.xza*` 2.7 GB | `html-2014.7za*` 10.4 GB | |
| 2017 | 860k | `archive-cc-2017.csv.gza*` 10.6 GB | `html-2017.tar.gza*` 20.2 GB | `meta-2017.tar.gza*` 2.6 GB |
| 2022 | 917k | `archive-cc-2022.csv.gza*` 12.6 GB | `html-2022.tar.gza*` 41.1 GB | `meta-2022.tar.gz` 2.1 GB |
| 2023 | 179k | `archive-cc-2023.csv.gz` 1.7 GB | `html-2023.tar.gza*` 7.3 GB | `meta-2023.tar.gz` 317 MB |

"No commercials" variants of the 2014, 2017, 2022 and 2023 CSVs were produced by notebooks that removed commercial segments from the `text` column; those notebooks are preserved at commit [`4182c3b`](https://github.com/notnews/archive_news_cc/tree/4182c3b/scripts/commercial).

**Record shape.** New runs write one JSON record per item and `to-parquet` builds a typed file with these columns:

| Column | Type | Source |
|---|---|---|
| `identifier` | string | archive.org item id, e.g. `CNNW_20260910_050000_The_Story_Is_With_Elex_Michaelson` |
| `title`, `contributor`, `description`, `language`, `runtime`, `closed_captioning` | string | item metadata; `contributor` is the station code |
| `aired_date` | date | metadata `date` |
| `publicdate` | string | when archive.org published the item |
| `text` | string | caption snippets joined with a space |
| `wordcount` | int32 | words in `text` |
| `caption_empty` | bool | true when no caption text was extracted (see Coverage) |
| `extra_json` | string | every other metadata field, as JSON |
| `source` | string | input file the row came from |

### Coverage

The `tvarchive` collection held 4,459,094 items on 2026-09-10 and grows by several thousand a day. The Dataverse runs cover 2009 to mid-2023. Two things to know before extending them:

- **Captions appear with a delay.** An item published minutes ago shows about 30 empty caption placeholders; the text is filled in later. Rows with `caption_empty = true` can be re-fetched with `fetch --refresh`, then parsed into a rebuilt JSONL without `--resume`; empty captions do not prove a silent broadcast.
- **The details page was the working public caption source in our checks.** Inspected items list caption files (`*.cc5.txt`, `*.align.srt`, `*.json`) but they are access-restricted: `/download/<id>/<id>.cc5.txt` returns 403 and `*.align.srt` returns an empty body. Scraping the 300 KB details page is not laziness; do not "optimize" it away.

### How the data were collected

Three steps, each a subcommand, each resumable:

1. **identifiers** queries the archive.org search API for `collection:tvarchive`, optionally filtered by air date, publication date (`--since`, for incremental runs) or station, and writes one JSONL record per item. Pagination uses the scrape API's cursor via the `internetarchive` library, so a query matching millions of items streams rather than truncating at one page as the previous implementation did.
2. **fetch** downloads each item's metadata (JSON API) to `data/meta/<id>_meta.json` and its details page to `data/html/<id>.html.gz`. Files are written atomically, so an interrupted run never leaves a truncated file that a later run would skip. Existing files are skipped; failures are appended to `data/fetch_failures.jsonl` and the run continues.
3. **parse** extracts caption text from `div.snipin.nosel` snippets and flattens metadata into JSONL. `--resume` appends only new identifiers.

The scripts that produced the four Dataverse runs used advancedsearch.php, `_meta.xml` files and a CSV writer; they are preserved at commit [`e78985d`](https://github.com/notnews/archive_news_cc/tree/e78985d). The 2026 rewrite fixed non-atomic downloads, a single-page search limit, and snippets joined without separators.

An interrupted, unterminated final JSONL record is removed before resuming; complete records are preserved. A valid final record missing only its newline is retained. Malformed complete lines remain errors.

### Usage

```bash
uv sync --group dev

# Items published since a date (incremental), capped for a trial
uv run archive-news-cc identifiers --since 2026-09-09 --limit 100 --out data/identifiers.jsonl

# Or an air-date window for one station
uv run archive-news-cc identifiers --contributor CNNW --start-date 2026-09-01 --end-date 2026-09-07

uv run archive-news-cc fetch data/identifiers.jsonl --max-workers 2 --min-interval 1
uv run archive-news-cc parse data/identifiers.jsonl --out data/captions.jsonl
uv run archive-news-cc to-parquet data/captions.jsonl --out data/archive_news_cc.parquet
uv run archive-news-cc upload data/archive_news_cc.parquet   # needs DATAVERSE_API_TOKEN
```

`fetch` and `parse` exit non-zero when any item failed or was missing, and list them, so a re-run can be targeted. Logs go to `data/archive_news_cc.log`.

Development: `uv run ruff check . && uv run ruff format --check . && uv run pytest`, or `uv run pre-commit install` once.

### Citation

See [CITATION.cff](CITATION.cff). Cite the Dataverse DOI for the data and credit the Internet Archive.

### License

Code is MIT. Captions and metadata are the Internet Archive's and the broadcasters'.

## Adjacent Repositories

- [notnews/lacc_to_csv](https://github.com/notnews/lacc_to_csv) — Los Angeles Closed-Caption Television News Archive Data to CSV
- [notnews/fox_news_transcripts](https://github.com/notnews/fox_news_transcripts) — Fox News Transcripts 2003--2025
- [notnews/cnn_transcripts](https://github.com/notnews/cnn_transcripts) — CNN Transcripts 2000--2025
- [notnews/msnbc_transcripts](https://github.com/notnews/msnbc_transcripts) — MSNBC Transcripts: 2003--2022
- [notnews/nbc_transcripts](https://github.com/notnews/nbc_transcripts) — NBC transcripts 2011--2014
