from __future__ import annotations

import json
import os

from fastapi import APIRouter, Request, Response

import config
import note_store
from core.folders import load_folders_registry, save_folders_registry

router = APIRouter()


@router.get("/api/folders")
async def list_folders():
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
    counts: dict[str, int] = {}
    for fn in os.listdir(config.TRANSCRIPTS_DIR):
        if not fn.endswith('.json'):
            continue
        try:
            with open(os.path.join(config.TRANSCRIPTS_DIR, fn), 'r') as f:
                data = json.load(f)
            folder = (data.get('folder') or '').strip()
            if folder:
                counts[folder] = counts.get(folder, 0) + 1
        except Exception:
            continue
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
    for fn in list(os.listdir(config.TRANSCRIPTS_DIR)):
        if not fn.endswith('.json'):
            continue
        json_path = os.path.join(config.TRANSCRIPTS_DIR, fn)
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            if (data.get('folder') or '').strip() != clean:
                continue
            base = os.path.splitext(fn)[0]
            audio_path = None
            try:
                audio_path = note_store._find_audio_path(base, data)  # type: ignore[attr-defined]
            except Exception:
                audio_path = None
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass
            try:
                os.remove(json_path)
            except Exception:
                pass
            deleted_notes += 1
        except Exception:
            continue
    normalized = [n for n in registry if n != clean]
    save_folders_registry(normalized)
    return {"deleted": clean, "notes_deleted": deleted_notes}
