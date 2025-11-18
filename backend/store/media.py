from __future__ import annotations

import logging
import os
import tempfile
import threading
from typing import Optional

import config
from store.api import AppwriteClient

logger = logging.getLogger(__name__)

_APPWRITE_STORAGE: Optional[AppwriteClient] = None
_APPWRITE_LOCK = threading.Lock()


def _client() -> AppwriteClient:
    global _APPWRITE_STORAGE
    if _APPWRITE_STORAGE is None:
        with _APPWRITE_LOCK:
            if _APPWRITE_STORAGE is None:
                _APPWRITE_STORAGE = AppwriteClient()
    return _APPWRITE_STORAGE


def is_appwrite_storage_enabled() -> bool:
    return (
        getattr(config, "STORE_BACKEND", "filesystem") == "appwrite"
        and bool(config.APPWRITE_BUCKET_VOICE_NOTES)
        and bool(config.APPWRITE_DATABASE_ID)
    )


def upload_audio_file(filename: str, data: bytes, mime: str) -> Optional[str]:
    if not is_appwrite_storage_enabled():
        logger.debug("Appwrite storage disabled; skipping upload for %s", filename)
        return None
    try:
        return _client().upload_file(config.APPWRITE_BUCKET_VOICE_NOTES, filename, data, mime)
    except Exception as e:
        logger.error("Failed to upload audio file %s (%s): %s", filename, mime, e, exc_info=True)
        return None


def delete_audio_file(file_id: Optional[str]) -> None:
    if not file_id:
        logger.debug("No Appwrite file_id provided for deletion; skipping.")
        return
    if not is_appwrite_storage_enabled():
        logger.debug("Appwrite storage disabled; cannot delete %s", file_id)
        return
    try:
        _client().delete_file(config.APPWRITE_BUCKET_VOICE_NOTES, file_id)
    except Exception as e:
        logger.error("Failed to delete Appwrite audio %s: %s", file_id, e, exc_info=True)


def download_audio_to_temp(file_id: str) -> Optional[str]:
    """Download an Appwrite audio file to a temp path.

    Returns the path to the temporary file, or None on failure.
    Caller is responsible for deleting the returned file.
    """
    if not file_id:
        logger.debug("No file_id supplied for download; skipping.")
        return None
    if not is_appwrite_storage_enabled():
        logger.debug("Appwrite storage disabled; cannot download %s", file_id)
        return None
    try:
        content = _client().download_file(config.APPWRITE_BUCKET_VOICE_NOTES, file_id)
        fd, path = tempfile.mkstemp(prefix="appwrite-audio-", suffix=".tmp")
        os.close(fd)
        with open(path, "wb") as f:
            f.write(content)
        return path
    except Exception as e:
        logger.error("Failed to download Appwrite audio %s: %s", file_id, e, exc_info=True)
        return None
