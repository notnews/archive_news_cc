## Closed Captions of News Videos from Archive.org

This repository provides a small CLI for fetching Archive.org TV news identifiers, downloading the corresponding raw files, and parsing them into structured records.

The project now uses `uv` and a `pyproject.toml` build.

Useful links:

- [CLI workflow](https://github.com/notnews/archive_news_cc#quickstart)
- [Data](https://github.com/notnews/archive_news_cc#data)

### What It Produces

The storage model is intentionally simple:

- raw source files: `.xml.gz` and `.html.gz`
- identifier lists: `jsonl`
- parsed show records: `jsonl.gz`
- run metadata: small `.json` manifests

This repo no longer treats CSV as the primary storage format.

### Quickstart

Install dependencies:

```bash
uv sync
```

See the CLI:

```bash
uv run archive-news-cc --help
```

The CLI has three subcommands:

- `archive-news-cc identifiers`
- `archive-news-cc scrape`
- `archive-news-cc parse`

### Typical Workflow

1. Fetch an identifier list from Archive.org.
2. Download metadata XML and caption HTML for those identifiers.
3. Parse the downloaded files into structured JSONL records.

Example:

```bash
uv run archive-news-cc identifiers \
  --sort "date desc" \
  --count 25 \
  --output data/identifiers.jsonl

uv run archive-news-cc scrape \
  --meta data/meta \
  --html data/html \
  data/identifiers.jsonl

uv run archive-news-cc parse \
  --meta data/meta \
  --html data/html \
  --outfile data/archive-out.jsonl.gz \
  data/identifiers.jsonl
```

### Latest Available Example

For a reproducible "latest data" run, fetch the latest available identifiers, save that exact identifier list, and parse from that saved list.

```bash
uv run archive-news-cc identifiers \
  --sort "date desc" \
  --count 25 \
  --output examples/runs/latest-2026-05-12/identifiers.jsonl
```

Then download and parse that exact slice:

```bash
uv run archive-news-cc scrape \
  --meta examples/runs/latest-2026-05-12/meta \
  --html examples/runs/latest-2026-05-12/html \
  examples/runs/latest-2026-05-12/identifiers.jsonl

uv run archive-news-cc parse \
  --meta examples/runs/latest-2026-05-12/meta \
  --html examples/runs/latest-2026-05-12/html \
  --outfile examples/runs/latest-2026-05-12/archive.jsonl.gz \
  examples/runs/latest-2026-05-12/identifiers.jsonl
```

There is also a checked-in example script at [examples/latest-news-window.sh](/Users/soodoku/Documents/GitHub/archive_news_cc/examples/latest-news-window.sh:1):

```bash
MAX_IDS=25 ./examples/latest-news-window.sh
```

That script writes:

- `identifiers.jsonl`
- `meta/`
- `html/`
- `archive.jsonl.gz`
- `manifest.json`

### Resumability

Resumability is intentionally narrow:

- `scrape` skips raw files that already exist on disk
- `parse --resume` skips identifiers already present in the output file
- `identifiers` writes a fresh immutable identifier list for each run

If parsing is interrupted:

```bash
uv run archive-news-cc parse --resume \
  --meta examples/runs/latest-2026-05-12/meta \
  --html examples/runs/latest-2026-05-12/html \
  --outfile examples/runs/latest-2026-05-12/archive.jsonl.gz \
  examples/runs/latest-2026-05-12/identifiers.jsonl
```

### Archive.org Access

The defaults are conservative on purpose:

- `scrape` defaults to `--max-workers 2`
- Archive.org requests default to `--min-request-interval 1.0`
- `429` and `503` responses back off and retry automatically
- a user-agent is sent on Archive.org requests

Each Archive.org-facing command also supports:

- `--request-timeout`
- `--min-request-interval`
- `--user-agent`

Logs go to `logs/` by default, and all commands support:

- `--log-level`
- `--log-dir`

### Record Shape

Parsed output is one JSON record per show. A typical record looks like:

```json
{
  "identifier": "KGO_20260513_003000_ABC_World_News_Tonight_With_David_Muir",
  "identifier_record": {
    "identifier": "KGO_20260513_003000_ABC_World_News_Tonight_With_David_Muir",
    "rank": 2,
    "query": "collection:\"tvarchive\"",
    "sort": "date desc",
    "fetched_at": "2026-05-13T04:00:00+00:00"
  },
  "source": {
    "meta_path": "data/meta/KGO_20260513_003000_ABC_World_News_Tonight_With_David_Muir_meta.xml.gz",
    "html_path": "data/html/KGO_20260513_003000_ABC_World_News_Tonight_With_David_Muir.html.gz"
  },
  "metadata": {
    "title": "ABC World News Tonight With David Muir",
    "date": "2026-05-13"
  },
  "transcript": {
    "text": "..."
  }
}
```

Metadata fields remain structured. Repeated XML tags are stored as arrays rather than flattened into one delimiter-separated string.

### Inputs and Outputs

`identifiers`

- queries Archive.org advanced search
- writes `jsonl` identifier records
- supports `--start-date`, `--end-date`, and `--sort`

`scrape`

- reads identifier records from `jsonl`
- downloads metadata XML and caption HTML
- writes raw files to `--meta` and `--html`

`parse`

- reads identifier records from `jsonl`
- reads raw files from `--meta` and `--html`
- writes parsed show records to `jsonl` or `jsonl.gz`

### Repository Layout

- `src/archive_news_cc/`: package code
- `examples/`: runnable example workflows

### Data

The data are hosted on [Harvard Dataverse](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/OAJJHI)

**Dataset Summary:**

1. **500k Dataset from 2014:**
   - CSV: `archive-cc-2014.csv.xza*` (2.7 GB, split into 2GB files)
   - HTML: `html-2014.7za*` (10.4 GB, split into 2GB files)

2. **860k Dataset from 2017:**
   - CSV: `archive-cc-2017.csv.gza*` (10.6 GB, split into 2GB files)
   - HTML: `html-2017.tar.gza*` (20.2 GB, split into 2GB files)
   - Meta: `meta-2017.tar.gza*` (2.6 GB, split into 2GB files)

3. **917k Dataset from 2022:**
   - CSV: `archive-cc-2022.csv.gza*` (12.6 GB, split into 2GB files)
   - HTML: `html-2022.tar.gza*` (41.1 GB, split into 2GB files)
   - Meta: `meta-2022.tar.gz` (2.1 GB)

4. **179k Dataset from 2023:**
   - CSV: `archive-cc-2023.csv.gz` (1.7 GB)
   - HTML: `html-2023.tar.gza*` (7.3 GB, split into 2GB files)
   - Meta: `meta-2023.tar.gz` (317 MB)

Please note that the file sizes and splitting information mentioned above are approximate.

### License

We are releasing the scripts under the [MIT License](https://opensource.org/licenses/MIT).

### Suggested Citation

Please credit Internet Archive for the data.

If you wanted to refer to this particular corpus so that the research is reproducible, you can cite it as:

```text
archive.org TV News Closed Caption Corpus. Laohaprapanon, Suriyan and Gaurav Sood. 2017. https://github.com/notnews/archive_news_cc/
```

## Adjacent Repositories

- [notnews/lacc_to_csv](https://github.com/notnews/lacc_to_csv) — Los Angeles Closed-Caption Television News Archive Data to CSV
- [notnews/fox_news_transcripts](https://github.com/notnews/fox_news_transcripts) — Fox News Transcripts 2003--2025
- [notnews/cnn_transcripts](https://github.com/notnews/cnn_transcripts) — CNN Transcripts 2000--2025
- [notnews/msnbc_transcripts](https://github.com/notnews/msnbc_transcripts) — MSNBC Transcripts: 2003--2022
- [notnews/nbc_transcripts](https://github.com/notnews/nbc_transcripts) — NBC transcripts 2011--2014
