#!/usr/bin/env python3
"""
Bootstrap Appwrite collections/attributes/buckets for Narrative Hero.

Usage:
    PYTHONPATH=. APPWRITE_ADMIN_KEY=<key-with-project-write> python scripts/setup_appwrite_schema.py

Reads the same APPWRITE_* env vars as the backend plus APPWRITE_ADMIN_KEY to
authorize schema operations. Collections/buckets are created if missing; existing
ones are left untouched.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List

import httpx

import config


def require(key: str) -> str:
    value = getattr(config, key, "") or ""
    if not value:
        raise SystemExit(f"Missing required env: {key}")
    return value


APPWRITE_ADMIN_KEY = os.getenv("APPWRITE_ADMIN_KEY") or config.APPWRITE_API_KEY
APPWRITE_ENDPOINT = require("APPWRITE_ENDPOINT").rstrip("/")
PROJECT_ID = require("APPWRITE_PROJECT_ID")
DATABASE_ID = require("APPWRITE_DATABASE_ID")


def headers() -> Dict[str, str]:
    if not APPWRITE_ADMIN_KEY:
        raise SystemExit("APPWRITE_ADMIN_KEY (or APPWRITE_API_KEY) is required for schema setup.")
    return {
        "X-Appwrite-Project": PROJECT_ID,
        "X-Appwrite-Key": APPWRITE_ADMIN_KEY,
        "Content-Type": "application/json",
    }


def ensure_collection(collection_id: str, name: str, permissions: List[str] | None = None) -> None:
    url = f"{APPWRITE_ENDPOINT}/databases/{DATABASE_ID}/collections/{collection_id}"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers())
        if resp.status_code == 200:
            return
        if resp.status_code != 404:
            raise SystemExit(f"Failed to inspect collection {collection_id}: {resp.text}")
    payload = {
        "collectionId": collection_id,
        "name": name,
        "permissions": permissions or [],
    }
    url = f"{APPWRITE_ENDPOINT}/databases/{DATABASE_ID}/collections"
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=headers(), json=payload)
        if resp.status_code not in (200, 201):
            raise SystemExit(f"Failed to create collection {collection_id}: {resp.text}")
    print(f"Created collection {collection_id} ({name})")


def wait_for_attribute(collection_id: str, attr_id: str, attempts: int = 20, delay: float = 1.0) -> None:
    url = f"{APPWRITE_ENDPOINT}/databases/{DATABASE_ID}/collections/{collection_id}/attributes/{attr_id}"
    for _ in range(attempts):
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers())
            if resp.status_code == 200:
                status = resp.json().get("status")
                if status and status.lower() != "processing":
                    return
        time.sleep(delay)
    raise SystemExit(f"Attribute {collection_id}.{attr_id} still processing; try rerunning later.")


def ensure_attribute(collection_id: str, attr: Dict[str, Any]) -> None:
    attr_id = attr["key"]
    url = f"{APPWRITE_ENDPOINT}/databases/{DATABASE_ID}/collections/{collection_id}/attributes/{attr_id}"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers())
        if resp.status_code == 200:
            return
        if resp.status_code != 404:
            raise SystemExit(f"Failed to inspect attribute {attr_id}: {resp.text}")
    attr_payload = {k: v for k, v in attr.items() if k not in {"type"}}
    url = f"{APPWRITE_ENDPOINT}/databases/{DATABASE_ID}/collections/{collection_id}/attributes/{attr['type']}"
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=headers(), json=attr_payload)
        if resp.status_code not in (200, 201, 202):
            raise SystemExit(f"Failed to create attribute {attr_id}: {resp.text}")
    wait_for_attribute(collection_id, attr_id)
    print(f"Created attribute {collection_id}.{attr_id}")


def ensure_bucket(bucket_id: str, name: str) -> None:
    url = f"{APPWRITE_ENDPOINT}/storage/buckets/{bucket_id}"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers())
        if resp.status_code == 200:
            return
        if resp.status_code != 404:
            raise SystemExit(f"Failed to inspect bucket {bucket_id}: {resp.text}")
    payload = {
        "bucketId": bucket_id,
        "name": name,
        "maximumFileSize": 1024 * 1024 * 200,
        "allowedFileExtensions": ["m4a", "mp3", "wav", "ogg", "webm"],
        "encryption": True,
        "antivirus": False,
    }
    url = f"{APPWRITE_ENDPOINT}/storage/buckets"
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=headers(), json=payload)
        if resp.status_code not in (200, 201):
            raise SystemExit(f"Failed to create bucket {bucket_id}: {resp.text}")
    print(f"Created bucket {bucket_id} ({name})")


NOTE_ATTRIBUTES: List[Dict[str, Any]] = [
    {"type": "string", "key": "filename", "size": 255, "required": True},
    {"type": "string", "key": "title", "size": 255, "required": True},
    {"type": "string", "key": "transcription", "size": 32767, "required": False},
    {"type": "string", "key": "date", "size": 32, "required": False},
    {"type": "string", "key": "created_at", "size": 64, "required": False},
    {"type": "integer", "key": "created_ts", "required": False, "min": -1_000_000_000_000, "max": 9_999_999_999_999},
    {"type": "float", "key": "length_seconds", "required": False},
    {"type": "string", "key": "language", "size": 16, "required": False},
    {"type": "string", "key": "folder", "size": 128, "required": False},
    {"type": "string", "key": "audio_format", "size": 16, "required": False},
    {"type": "string", "key": "stored_mime", "size": 64, "required": False},
    {"type": "string", "key": "original_format", "size": 16, "required": False},
    {"type": "boolean", "key": "transcoded", "required": False, "default": False},
    {"type": "string", "key": "transcoded_from", "size": 16, "required": False},
    {"type": "string", "key": "content_type", "size": 64, "required": False},
    {"type": "string", "key": "upload_extension", "size": 16, "required": False},
    {"type": "integer", "key": "sample_rate_hz", "required": False, "min": 0, "max": 48000},
    {"type": "string", "key": "appwrite_file_id", "size": 64, "required": False},
    {"type": "string", "key": "auto_category", "size": 64, "required": False},
    {"type": "float", "key": "auto_category_confidence", "required": False},
    {"type": "string", "key": "auto_program", "size": 64, "required": False},
    {"type": "float", "key": "auto_program_confidence", "required": False},
    {"type": "string", "key": "auto_program_rationale", "size": 2048, "required": False},
    {"type": "string", "key": "topics_json", "size": 2048, "required": False},
    {"type": "string", "key": "tags_json", "size": 2048, "required": False},
]

PROGRAM_ATTRIBUTES: List[Dict[str, Any]] = [
    {"type": "string", "key": "title", "size": 255, "required": True},
    {"type": "string", "key": "description", "size": 2048, "required": False},
    {"type": "string", "key": "domain", "size": 64, "required": False},
    {"type": "string", "key": "status", "size": 32, "required": False},
    {"type": "string", "key": "filename_prefix", "size": 64, "required": False},
    {"type": "string", "key": "color", "size": 16, "required": False},
    {"type": "string", "key": "keywords_json", "size": 2048, "required": False},
    {"type": "string", "key": "tags_json", "size": 1024, "required": False},
    {"type": "string", "key": "aliases_json", "size": 1024, "required": False},
    {"type": "string", "key": "owners_json", "size": 1024, "required": False},
]

FOLDER_ATTRIBUTES: List[Dict[str, Any]] = [
    {"type": "string", "key": "name", "size": 128, "required": True},
]

FORMAT_ATTRIBUTES: List[Dict[str, Any]] = [
    {"type": "string", "key": "title", "size": 255, "required": True},
    {"type": "string", "key": "prompt", "size": 32767, "required": True},
]

NARRATIVE_ATTRIBUTES: List[Dict[str, Any]] = [
    {"type": "string", "key": "filename", "size": 255, "required": True},
    {"type": "string", "key": "title", "size": 255, "required": False},
    {"type": "string", "key": "content", "size": 32767, "required": False},
    {"type": "string", "key": "folder", "size": 128, "required": False},
]


def main() -> None:
    ensure_collection(config.APPWRITE_NOTES_COLLECTION_ID, "Notes")
    ensure_collection(config.APPWRITE_PROGRAMS_COLLECTION_ID, "Programs")
    ensure_collection(config.APPWRITE_FOLDERS_COLLECTION_ID, "Folders")
    ensure_collection(config.APPWRITE_FORMATS_COLLECTION_ID, "Formats")
    ensure_collection(config.APPWRITE_NARRATIVES_COLLECTION_ID, "Narratives")

    for attr in NOTE_ATTRIBUTES:
        ensure_attribute(config.APPWRITE_NOTES_COLLECTION_ID, attr)
    for attr in PROGRAM_ATTRIBUTES:
        ensure_attribute(config.APPWRITE_PROGRAMS_COLLECTION_ID, attr)
    for attr in FOLDER_ATTRIBUTES:
        ensure_attribute(config.APPWRITE_FOLDERS_COLLECTION_ID, attr)
    for attr in FORMAT_ATTRIBUTES:
        ensure_attribute(config.APPWRITE_FORMATS_COLLECTION_ID, attr)
    for attr in NARRATIVE_ATTRIBUTES:
        ensure_attribute(config.APPWRITE_NARRATIVES_COLLECTION_ID, attr)

    ensure_bucket(config.APPWRITE_BUCKET_VOICE_NOTES, "Voice Notes")
    if config.APPWRITE_BUCKET_NARRATIVES:
        ensure_bucket(config.APPWRITE_BUCKET_NARRATIVES, "Narratives")

    print("Appwrite schema bootstrap complete.")


if __name__ == "__main__":
    main()
