#!/usr/bin/env python3
"""Migrate local JSON/audio notes into Appwrite collections/buckets.

Usage:
    STORE_BACKEND=filesystem python backend/scripts/migrate_to_appwrite.py

The script expects Appwrite env vars (APPWRITE_ENDPOINT, PROJECT_ID, API_KEY,
database + collection IDs, bucket IDs) to be set in .env or the shell.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Optional

import config
from store.api import AppwriteClient
from store.appwrite import serialize_note_payload


def require_env(name: str) -> str:
    value = getattr(config, name, None)
    if not value:
        raise SystemExit(f"Missing required Appwrite env: {name}")
    return value


def upload_audio(client: AppwriteClient, path: Path, filename: str, mime: str) -> Optional[str]:
    if not path.exists():
        return None
    with path.open("rb") as fh:
        data = fh.read()
    if not data:
        return None
    return client.upload_file(config.APPWRITE_BUCKET_VOICE_NOTES, filename, data, mime)


def migrate_notes(client: AppwriteClient, dry_run: bool = False) -> None:
    notes_dir = Path(config.TRANSCRIPTS_DIR)
    audio_dir = Path(config.VOICE_NOTES_DIR)
    total = 0
    migrated = 0
    for json_path in sorted(notes_dir.glob("*.json")):
        total += 1
        base = json_path.stem
        try:
            data = json.loads(json_path.read_text())
        except Exception:
            print(f"Skipping {json_path.name}: unreadable JSON")
            continue
        filename = data.get("filename") or f"{base}.wav"
        audio_path = (audio_dir / filename)
        stored_mime = data.get("stored_mime") or "audio/wav"
        file_id = None
        if not dry_run and audio_path.exists():
            try:
                file_id = upload_audio(client, audio_path, filename, stored_mime)
            except Exception as exc:
                print(f"Failed to upload audio for {filename}: {exc}")
        if file_id:
            data["appwrite_file_id"] = file_id
        if dry_run:
            print(f"[dry-run] would upsert note {base}")
            continue
        prepared = serialize_note_payload(data)
        try:
            client.update_document(config.APPWRITE_NOTES_COLLECTION_ID, base, prepared)
        except Exception:
            client.create_document(config.APPWRITE_NOTES_COLLECTION_ID, base, prepared)
        migrated += 1
    print(f"Notes processed: {total}; migrated: {migrated}")


def _jsonify(entry: dict, key: str) -> None:
    if key in entry:
        entry[f"{key}_json"] = json.dumps(entry.get(key, []))
        entry.pop(key, None)


def migrate_programs(client: AppwriteClient, dry_run: bool = False) -> None:
    path = Path(config.PROGRAMS_DIR) / "programs.json"
    if not path.exists():
        return
    try:
        programs = json.loads(path.read_text())
    except Exception:
        print("Skipping programs registry: unreadable JSON")
        return
    if dry_run:
        print(f"[dry-run] would upsert {len(programs)} programs")
        return
    for entry in programs:
        key = entry.get("key")
        if not key:
            continue
        payload = dict(entry)
        payload.pop("key", None)
        for fld in ("keywords", "tags", "aliases", "owners"):
            _jsonify(payload, fld)
        try:
            client.update_document(config.APPWRITE_PROGRAMS_COLLECTION_ID, key, payload)
        except Exception:
            client.create_document(config.APPWRITE_PROGRAMS_COLLECTION_ID, key, payload)
    print(f"Programs migrated: {len(programs)}")


def migrate_folders(client: AppwriteClient, dry_run: bool = False) -> None:
    path = Path(config.FOLDERS_DIR) / "folders.json"
    if not path.exists():
        return
    try:
        folders = json.loads(path.read_text())
    except Exception:
        print("Skipping folders registry: unreadable JSON")
        return
    names = [str(n).strip() for n in folders if isinstance(n, str) and n.strip()]
    if dry_run:
        print(f"[dry-run] would upsert {len(names)} folders")
        return
    for name in names:
        doc = {"name": name}
        try:
            client.update_document(config.APPWRITE_FOLDERS_COLLECTION_ID, name, doc)
        except Exception:
            client.create_document(config.APPWRITE_FOLDERS_COLLECTION_ID, name, doc)
    print(f"Folders migrated: {len(names)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate local storage to Appwrite")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    require_env("APPWRITE_ENDPOINT")
    require_env("APPWRITE_PROJECT_ID")
    require_env("APPWRITE_API_KEY")
    require_env("APPWRITE_DATABASE_ID")
    require_env("APPWRITE_NOTES_COLLECTION_ID")
    require_env("APPWRITE_BUCKET_VOICE_NOTES")

    client = AppwriteClient()
    migrate_notes(client, dry_run=args.dry_run)
    if getattr(config, "APPWRITE_PROGRAMS_COLLECTION_ID", None):
        migrate_programs(client, dry_run=args.dry_run)
    if getattr(config, "APPWRITE_FOLDERS_COLLECTION_ID", None):
        migrate_folders(client, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
