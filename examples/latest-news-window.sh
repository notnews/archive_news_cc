#!/usr/bin/env bash

set -euo pipefail

MAX_IDS="${MAX_IDS:-25}"
RUN_LABEL="${RUN_LABEL:-$(date -u +"%Y-%m-%d")}"
OUT_DIR="${OUT_DIR:-examples/runs/latest-${RUN_LABEL}}"

mkdir -p "${OUT_DIR}"

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

manifest = {
    "sort": "date desc",
    "max_ids": int("${MAX_IDS}"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
}
Path("${OUT_DIR}/manifest.json").write_text(json.dumps(manifest, indent=2) + "\\n")
PY

uv run archive-news-cc identifiers \
  --sort "date desc" \
  --count "${MAX_IDS}" \
  --output "${OUT_DIR}/identifiers.jsonl"

uv run archive-news-cc scrape \
  --meta "${OUT_DIR}/meta" \
  --html "${OUT_DIR}/html" \
  "${OUT_DIR}/identifiers.jsonl"

uv run archive-news-cc parse \
  --meta "${OUT_DIR}/meta" \
  --html "${OUT_DIR}/html" \
  --outfile "${OUT_DIR}/archive.jsonl.gz" \
  "${OUT_DIR}/identifiers.jsonl"
