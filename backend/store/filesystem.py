"""
Filesystem-backed NotesStore implementation.

This wraps the existing note_store helpers so callers can speak through the
abstract interface while the underlying behavior remains unchanged.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable

import config
import note_store
from store.base import NotesStore


class FilesystemNotesStore(NotesStore):
    def save_note(self, base_id: str, payload: Dict[str, Any]) -> None:
        note_store.save_note_json(base_id, payload)

    def load_note(self, base_id: str):
        return note_store.load_note_json(base_id)

    def list_notes(self) -> Iterable[Dict[str, Any]]:
        if not os.path.isdir(config.TRANSCRIPTS_DIR):
            return []
        for fn in sorted(os.listdir(config.TRANSCRIPTS_DIR)):
            if not fn.endswith(".json"):
                continue
            base = os.path.splitext(fn)[0]
            data, _, _ = note_store.load_note_json(base)
            if data:
                yield data

    def delete_note(self, base_id: str) -> None:
        path = note_store.note_json_path(base_id)
        if os.path.exists(path):
            os.remove(path)
