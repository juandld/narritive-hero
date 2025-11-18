"""
Appwrite-backed NotesStore implementation.

Persists note metadata to Appwrite collections so STORE_BACKEND=appwrite can
operate without relying on the local filesystem JSON store.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional, Tuple

import config
from store.base import NotesStore
from store.api import AppwriteClient

NOTE_ALLOWED_FIELDS = {
    "filename",
    "title",
    "transcription",
    "date",
    "created_at",
    "created_ts",
    "length_seconds",
    "language",
    "folder",
    "audio_format",
    "stored_mime",
    "original_format",
    "transcoded",
    "transcoded_from",
    "content_type",
    "upload_extension",
    "sample_rate_hz",
    "appwrite_file_id",
    "auto_category",
    "auto_category_confidence",
    "auto_program",
    "auto_program_confidence",
    "auto_program_rationale",
}


def serialize_note_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    doc: Dict[str, Any] = {}
    for key in NOTE_ALLOWED_FIELDS:
        if key in payload:
            value = payload[key]
            if value is not None:
                doc[key] = value
    doc["topics_json"] = json.dumps(payload.get("topics") or [])
    doc["tags_json"] = json.dumps(payload.get("tags") or [])
    return doc


def deserialize_note_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(doc)
    if "topics_json" in data:
        try:
            data["topics"] = json.loads(data.pop("topics_json") or "[]")
        except Exception:
            data["topics"] = []
    if "tags_json" in data:
        try:
            data["tags"] = json.loads(data.pop("tags_json") or "[]")
        except Exception:
            data["tags"] = []
    else:
        data.setdefault("tags", [])
    data.setdefault("topics", [])
    return data


class AppwriteNotesStore(NotesStore):
    def __init__(self) -> None:
        self._client = AppwriteClient()
        if not config.APPWRITE_DATABASE_ID:
            raise RuntimeError("APPWRITE_DATABASE_ID is required for Appwrite storage.")
        if not config.APPWRITE_NOTES_COLLECTION_ID:
            raise RuntimeError("APPWRITE_NOTES_COLLECTION_ID is required for Appwrite storage.")

    def save_note(self, base_id: str, payload: Dict[str, Any]) -> None:
        prepared = serialize_note_payload(payload)
        doc = self._client.get_document(config.APPWRITE_NOTES_COLLECTION_ID, base_id)
        if doc:
            self._client.update_document(config.APPWRITE_NOTES_COLLECTION_ID, base_id, prepared)
        else:
            self._client.create_document(config.APPWRITE_NOTES_COLLECTION_ID, base_id, prepared)

    def load_note(self, base_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        doc = self._client.get_document(config.APPWRITE_NOTES_COLLECTION_ID, base_id)
        if not doc:
            return None, None, None
        data = deserialize_note_document(doc.get("data") or doc)
        return data, data.get("transcription"), data.get("title")

    def list_notes(self) -> Iterable[Dict[str, Any]]:
        cursor: Optional[str] = None
        page_size = 100
        while True:
            batch = self._client.list_documents(
                config.APPWRITE_NOTES_COLLECTION_ID,
                limit=page_size,
                cursor=cursor,
            )
            documents = batch.get("documents", []) or []
            if not documents:
                break
            for item in documents:
                data = deserialize_note_document(item.get("data") or item)
                if "$id" in item and "$id" not in data:
                    data.setdefault("$id", item["$id"])
                yield data
            if len(documents) < page_size:
                break
            cursor = documents[-1].get("$id")
            if not cursor:
                break

    def delete_note(self, base_id: str) -> None:
        self._client.delete_document(config.APPWRITE_NOTES_COLLECTION_ID, base_id)
