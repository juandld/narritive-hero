from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, Response, UploadFile

import config
from core import note_logic
from models import FolderUpdate, TagsUpdate
from services import get_notes, transcribe_and_save
from store import get_notes_store
from store.media import delete_audio_file

router = APIRouter()
NOTES_STORE = get_notes_store()


@router.get("/api/notes")
async def read_notes():
    return get_notes()


@router.post("/api/notes")
async def create_note(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    date: str = Form(None),
    place: str = Form(None),
    folder: str = Form(None),
):
    try:
        return await note_logic.process_audio_upload(file, background_tasks, date, place, folder)
    except RuntimeError as exc:
        return Response(status_code=400, content=str(exc))


@router.post("/api/notes/{filename}/retry")
async def retry_note(background_tasks: BackgroundTasks, filename: str):
    file_path = os.path.join(config.VOICE_NOTES_DIR, filename)
    if not os.path.exists(file_path):
        return Response(status_code=404)
    background_tasks.add_task(transcribe_and_save, file_path)  # type: ignore[name-defined]
    return {"status": "queued"}


@router.delete("/api/notes/{filename}")
async def delete_note(filename: str):
    base_filename = os.path.splitext(filename)[0]
    deleted = False
    data = None
    try:
        data, _, _ = NOTES_STORE.load_note(base_filename)
    except Exception:
        data = None
    file_id = (data or {}).get('appwrite_file_id') if data else None
    audio_path = os.path.join(config.VOICE_NOTES_DIR, filename)
    if os.path.exists(audio_path):
        try:
            os.remove(audio_path)
            deleted = True
        except Exception:
            pass
    if file_id:
        delete_audio_file(file_id)
    try:
        NOTES_STORE.delete_note(base_filename)
        deleted = True
    except Exception:
        pass
    return Response(status_code=200 if deleted else 404)


@router.post("/api/notes/text")
async def create_text_note(request: Request):
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=400)
    try:
        return await note_logic.create_note_from_text_payload(body, include_summary=True)
    except ValueError:
        return Response(status_code=400)
    except Exception as e:
        return {"error": str(e)}


@router.patch("/api/notes/{filename}/tags")
async def update_tags(filename: str, payload: TagsUpdate):
    base_filename = os.path.splitext(filename)[0]
    try:
        data, _, _ = NOTES_STORE.load_note(base_filename)
        if not data:
            return Response(status_code=404)
        tags = [{"label": t.label, "color": t.color} for t in payload.tags]
        data["tags"] = tags
        NOTES_STORE.save_note(base_filename, data)
        return {"status": "ok", "tags": tags}
    except Exception as e:
        return {"error": str(e)}


@router.patch("/api/notes/{filename}/folder")
async def update_folder(filename: str, payload: FolderUpdate):
    base_filename = os.path.splitext(filename)[0]
    desired_folder = str(payload.folder or "").strip()
    try:
        data, _, _ = NOTES_STORE.load_note(base_filename)
        if not data:
            return Response(status_code=404)
        data["folder"] = desired_folder
        NOTES_STORE.save_note(base_filename, data)
        return {"status": "ok", "folder": data["folder"]}
    except Exception as e:
        return {"error": str(e)}
