from __future__ import annotations

import os
import tempfile
from typing import Optional

import config
from store.api import AppwriteClient

_APPWRITE_STORAGE: Optional[AppwriteClient] = None


def _client() -> AppwriteClient:
    global _APPWRITE_STORAGE
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
        return None
    try:
        return _client().upload_file(config.APPWRITE_BUCKET_VOICE_NOTES, filename, data, mime)
    except Exception:
        return None


def delete_audio_file(file_id: Optional[str]) -> None:
    if not file_id or not is_appwrite_storage_enabled():
        return
    try:
        _client().delete_file(config.APPWRITE_BUCKET_VOICE_NOTES, file_id)
    except Exception:
        pass


def download_audio_to_temp(file_id: str) -> Optional[str]:
    if not file_id or not is_appwrite_storage_enabled():
        return None
    try:
        content = _client().download_file(config.APPWRITE_BUCKET_VOICE_NOTES, file_id)
        fd, path = tempfile.mkstemp(prefix="appwrite-audio-", suffix=".tmp")
        os.close(fd)
        with open(path, "wb") as f:
            f.write(content)
        return path
    except Exception:
        return None
