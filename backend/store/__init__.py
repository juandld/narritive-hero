"""
Storage backend factory.

Use `get_notes_store()` to obtain the configured NotesStore implementation.
"""

from __future__ import annotations

from typing import Optional

import config
from store.base import NotesStore
from store.filesystem import FilesystemNotesStore

_NOTES_STORE: Optional[NotesStore] = None


def get_notes_store(force_refresh: bool = False) -> NotesStore:
    global _NOTES_STORE
    if _NOTES_STORE is not None and not force_refresh:
        return _NOTES_STORE

    backend = getattr(config, "STORE_BACKEND", "filesystem")
    if backend == "filesystem":
        _NOTES_STORE = FilesystemNotesStore()
    elif backend == "appwrite":
        from store.appwrite import AppwriteNotesStore

        _NOTES_STORE = AppwriteNotesStore()
    else:
        raise ValueError(f"Unsupported STORE_BACKEND={backend}")
    return _NOTES_STORE
