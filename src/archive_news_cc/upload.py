"""Upload a file to the Dataverse dataset that hosts the corpus."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pyDataverse.api import NativeApi

if TYPE_CHECKING:
    from pathlib import Path

DATAVERSE_URL = "https://dataverse.harvard.edu"
DATASET_DOI = "doi:10.7910/DVN/OAJJHI"
TOKEN_ENV = "DATAVERSE_API_TOKEN"  # noqa: S105 - variable name, not a secret


def upload(path: Path, doi: str = DATASET_DOI, base_url: str = DATAVERSE_URL) -> str:
    """Add ``path`` to the dataset identified by ``doi``.

    Args:
        path: File to upload.
        doi: Persistent identifier of the dataset, ``doi:`` prefix included.
        base_url: Dataverse installation.

    Returns:
        The server's JSON response as text.

    Raises:
        SystemExit: If the API token environment variable is not set, or the
            server rejects the upload.
    """
    token = os.environ.get(TOKEN_ENV)
    if not token:
        raise SystemExit(f"set {TOKEN_ENV} to a Dataverse API token")
    api = NativeApi(base_url, token)
    response = api.upload_datafile(doi, str(path), is_pid=True)
    if response.status_code >= 300:
        raise SystemExit(f"upload failed ({response.status_code}): {response.text}")
    return response.text
