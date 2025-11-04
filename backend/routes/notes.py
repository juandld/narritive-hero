from __future__ import annotations

import json
import os

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, Response, UploadFile

import config
from core import note_logic
from models import FolderUpdate, TagsUpdate
from note_store import ensure_metadata_in_json
from services import get_notes, transcribe_and_save

router = APIRouter()


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
    file_path = os.path.join(config.VOICE_NOTES_DIR, filename)
    base_filename = os.path.splitext(filename)[0]
    json_path = os.path.join(config.TRANSCRIPTS_DIR, f"{base_filename}.json")
    legacy_txt_path = os.path.join(config.TRANSCRIPTS_DIR, f"{base_filename}.txt")
    deleted_any = False
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            deleted_any = True
        except Exception:
            pass
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
            deleted_any = True
        except Exception:
            pass
    if os.path.exists(legacy_txt_path):
        try:
            os.remove(legacy_txt_path)
            deleted_any = True
        except Exception:
            pass
    return Response(status_code=200 if deleted_any else 404)


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
    json_path = os.path.join(config.TRANSCRIPTS_DIR, f"{base_filename}.json")
    if not os.path.exists(json_path):
        return Response(status_code=404)
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        tags = [{"label": t.label, "color": t.color} for t in payload.tags]
        data["tags"] = tags
        with open(json_path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        return {"status": "ok", "tags": tags}
    except Exception as e:
        return {"error": str(e)}


@router.patch("/api/notes/{filename}/folder")
async def update_folder(filename: str, payload: FolderUpdate):
    base_filename = os.path.splitext(filename)[0]
    json_path = os.path.join(config.TRANSCRIPTS_DIR, f"{base_filename}.json")
    desired_folder = str(payload.folder or "").strip()

    if not os.path.exists(json_path):
        from note_store import build_note_payload

        try:
            audio_path = os.path.join(config.VOICE_NOTES_DIR, filename)
            if not os.path.exists(audio_path):
                for ext in (".wav", ".ogg", ".webm", ".m4a", ".mp3"):
                    candidate = os.path.join(config.VOICE_NOTES_DIR, base_filename + ext)
                    if os.path.exists(candidate):
                        audio_path = candidate
                        filename = os.path.basename(candidate)
                        break
            audio_ext = os.path.splitext(filename)[1].lstrip(".").lower() or "wav"
            stored_mime = {
                "m4a": "audio/mp4",
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
                "ogg": "audio/ogg",
                "webm": "audio/webm",
            }.get(audio_ext, f"audio/{audio_ext}" if audio_ext else "audio/wav")
            metadata_fields = {
                "audio_format": audio_ext,
                "stored_mime": stored_mime,
                "original_format": audio_ext,
                "transcoded": False,
            }
            if audio_ext == "m4a":
                metadata_fields["sample_rate_hz"] = 44100
            elif audio_ext == "wav":
                metadata_fields["sample_rate_hz"] = 16000
            payload_min = build_note_payload(filename, base_filename, "", metadata_fields)
            with open(json_path, "w") as f:
                json.dump(payload_min, f, ensure_ascii=False)
        except Exception:
            return Response(status_code=404)

    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        data["folder"] = desired_folder
        ensure_metadata_in_json(base_filename, data)
        with open(json_path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        return {"status": "ok", "folder": data["folder"]}
    except Exception as e:
        return {"error": str(e)}
