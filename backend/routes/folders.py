from __future__ import annotations

import json
import os

from fastapi import APIRouter, Request, Response

import config
from core.folders import load_folders_registry, save_folders_registry
from store.media import delete_audio_file
from store import get_notes_store

router = APIRouter()
NOTES_STORE = get_notes_store()


@router.get("/api/folders")
async def list_folders():
    counts: dict[str, int] = {}
    try:
        for note in NOTES_STORE.list_notes():
            folder = (note.get("folder") or "").strip()
            if folder:
                counts[folder] = counts.get(folder, 0) + 1
    except Exception:
        pass
    registry = load_folders_registry()
    for name in registry:
        counts.setdefault(name, 0)
    return [{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: kv[0].lower())]


@router.post("/api/folders")
async def create_folder(request: Request):
    try:
        body = await request.json()
        name = str((body or {}).get("name") or "").strip()
        if not name:
            return Response(status_code=400)
        if "/" in name or "\\" in name:
            return Response(status_code=400)
        registry = load_folders_registry()
        if name not in registry:
            registry.append(name)
            save_folders_registry(registry)
        return {"name": name}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/api/folders/{name}")
async def delete_folder(name: str):
    clean = (name or "").strip()
    registry = load_folders_registry()
    deleted_notes = 0
    try:
        for note in list(NOTES_STORE.list_notes()):
            folder = (note.get("folder") or "").strip()
            if folder != clean:
                continue
            filename = note.get("filename")
            file_id = note.get("appwrite_file_id")
            if filename:
                audio_path = os.path.join(config.VOICE_NOTES_DIR, filename)
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass
            if file_id:
                delete_audio_file(file_id)
            NOTES_STORE.delete_note(os.path.splitext(filename or "")[0])
            deleted_notes += 1
    except Exception:
        pass
    normalized = [n for n in registry if n != clean]
    save_folders_registry(normalized)
    return {"deleted": clean, "notes_deleted": deleted_notes}
