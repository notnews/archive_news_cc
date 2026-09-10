"""Repair only an interrupted final line before appending to a checkpoint."""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def prepare_checkpoint(path: Path) -> None:
    """Keep complete rows and discard an incomplete, unterminated final record."""
    if not path.exists() or not path.stat().st_size:
        return
    with path.open("r+b") as handle:
        end = handle.seek(0, 2)
        handle.seek(end - 1)
        if handle.read(1) == b"\n":
            return
        start = end
        while start:
            lower = max(0, start - 8192)
            handle.seek(lower)
            chunk = handle.read(start - lower)
            newline = chunk.rfind(b"\n")
            if newline >= 0:
                start = lower + newline + 1
                break
            start = lower
        handle.seek(start)
        tail = handle.read()
        try:
            json.loads(tail)
        except (json.JSONDecodeError, UnicodeDecodeError):
            handle.truncate(start)
            log.warning("discarded incomplete final checkpoint record in %s", path)
        else:
            handle.seek(0, 2)
            handle.write(b"\n")
