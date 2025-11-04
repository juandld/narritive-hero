from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, Response, UploadFile

import config
from core import note_logic

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_tags(value: object) -> list[dict]:
    tags: list[dict] = []
    if not value:
        return tags
    try:
        parsed = value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return tags
            try:
                parsed = json.loads(value)
            except Exception:
                parsed = [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(parsed, dict):
            for key, v in parsed.items():
                label = str(key or "").strip()
                if not label:
                    continue
                color = v.get("color") if isinstance(v, dict) else None
                tags.append({"label": label, "color": color})
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, str):
                    label = item.strip()
                    if label:
                        tags.append({"label": label})
                elif isinstance(item, dict):
                    label = str((item.get("label") or item.get("name") or item.get("title") or "")).strip()
                    if label:
                        tag_entry = {"label": label}
                        if item.get("color"):
                            tag_entry["color"] = item.get("color")
                        tags.append(tag_entry)
        else:
            label = str(parsed or "").strip()
            if label:
                tags.append({"label": label})
    except Exception:
        label = str(value or "").strip()
        if label:
            tags.append({"label": label})
    seen: set[str] = set()
    deduped: list[dict] = []
    for tag in tags:
        label = str((tag.get("label") or "")).strip()
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"label": label, "color": tag.get("color")})
    return deduped


@router.post("/api/integrations/telegram")
async def ingest_telegram_message(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    transcription_form: Optional[str] = Form(None),
    title_form: Optional[str] = Form(None),
    date_form: Optional[str] = Form(None),
    folder_form: Optional[str] = Form(None, alias="folder"),
    tags_form: Optional[str] = Form(None, alias="tags"),
):
    shared_token = getattr(config, "N8N_WEBHOOK_TOKEN", None)
    provided_token = (
        request.headers.get("x-webhook-token")
        or request.headers.get("x-n8n-token")
        or request.query_params.get("token")
    )
    auth_header = request.headers.get("authorization")
    if not provided_token and auth_header and auth_header.lower().startswith("bearer "):
        provided_token = auth_header[7:].strip()
    if shared_token:
        if not provided_token or provided_token != shared_token:
            return Response(status_code=401)

    try:
        body = await request.json()
    except Exception:
        body = {}

    query_params = request.query_params
    title_value = (
        title_form
        or str((body or {}).get("title") or (body or {}).get("subject") or "").strip()
        or query_params.get("title")
        or ""
    )
    date_value = (
        date_form
        or str(
            (body or {}).get("date")
            or (body or {}).get("sentAt")
            or (body or {}).get("sent_at")
            or (body or {}).get("timestamp")
            or query_params.get("date")
            or ""
        ).strip()
    )
    if (folder_form is None or folder_form == "") and file is not None:
        try:
            form_data = await request.form()
            folder_candidate = form_data.get("folder") if form_data else None
            if folder_candidate:
                folder_form = str(folder_candidate)
        except Exception:
            pass
    folder_value = (
        folder_form
        or str((body or {}).get("folder") or query_params.get("folder") or "").strip()
    )
    tags_payload = tags_form or (body or {}).get("tags") or query_params.get("tags")
    tags = _parse_tags(tags_payload)
    if not any((t.get("label") or "").lower() == "telegram" for t in tags):
        tags.append({"label": "telegram"})

    if file is not None:
        try:
            upload_result = await note_logic.process_audio_upload(
                file=file,
                background_tasks=background_tasks,
                date=date_value or None,
                place=None,
                folder=folder_value or None,
            )
        except RuntimeError as e:
            return {"error": f"Upload failed: {e}"}
        filename = upload_result.get("filename") if isinstance(upload_result, dict) else None
        if not filename:
            return {"error": "Upload failed"}

        base_name = os.path.splitext(filename)[0]
        json_path = os.path.join(config.TRANSCRIPTS_DIR, f"{base_name}.json")
        note_data: Dict[str, Any]
        try:
            if os.path.exists(json_path):
                with open(json_path, "r") as jf:
                    note_data = json.load(jf)
            else:
                note_data = {
                    "filename": filename,
                    "title": os.path.splitext(filename)[0],
                    "transcription": "",
                }
        except Exception:
            note_data = {
                "filename": filename,
                "title": os.path.splitext(filename)[0],
                "transcription": "",
            }

        if folder_value:
            note_data["folder"] = folder_value
        if tags:
            note_data["tags"] = tags
        else:
            note_data.setdefault("tags", [{"label": "telegram"}])
        try:
            with open(json_path, "w") as jf:
                json.dump(note_data, jf, ensure_ascii=False)
        except Exception:
            pass

        summary = None
        transcription_status = "pending"
        title_final = note_data.get("title") or os.path.splitext(filename)[0]
        created_at = note_data.get("created_at")
        created_ts = note_data.get("created_ts")
        deadline = time.time() + 30

        while True:
            try:
                if os.path.exists(json_path):
                    with open(json_path, "r") as jf:
                        note_data = json.load(jf)
            except Exception:
                continue
            transcription_text = str(note_data.get("transcription") or "").strip()
            title_candidate = str(note_data.get("title") or "").strip()
            if title_candidate:
                title_final = title_candidate
            created_at = note_data.get("created_at", created_at)
            created_ts = note_data.get("created_ts", created_ts)
            if transcription_text and transcription_text != "Transcription failed.":
                summary = await note_logic.summarize_text_snippet(transcription_text)
                classification = note_logic.apply_classification(note_data, title_final, transcription_text)
                if classification is not None:
                    try:
                        with open(json_path, "w") as jf:
                            json.dump(note_data, jf, ensure_ascii=False)
                    except Exception:
                        pass
                transcription_status = "complete"
                break
            if transcription_text == "Transcription failed.":
                transcription_status = "failed"
                break
            if time.time() >= deadline:
                break
            await asyncio.sleep(3)

        folder_final = folder_value or str(note_data.get("folder") or "").strip()
        status_bits = [f"Saved “{title_final or filename}”"]
        if folder_final:
            status_bits.append(f"in folder “{folder_final}”")
        else:
            status_bits.append("to your uncategorized inbox")
        if tags:
            tag_labels = [t["label"] for t in tags if t.get("label")]
            if tag_labels:
                shown = ", ".join(tag_labels[:3])
                if len(tag_labels) > 3:
                    shown += ", …"
                status_bits.append(f"tags: {shown}")
        if note_data.get("auto_category"):
            status_bits.append(f"auto category: {note_data.get('auto_category')}")
        if note_data.get("auto_program"):
            status_bits.append(f"program: {note_data.get('auto_program')}")
        if transcription_status == "pending":
            status_bits.append("transcription in progress")
        elif transcription_status == "failed":
            status_bits.append("transcription failed – retry from the app")
        else:
            status_bits.append("transcription ready")
        status_message = "; ".join(status_bits) + "."

        response: Dict[str, Any] = {
            "source": "telegram",
            "input_type": "audio",
            "filename": filename,
            "title": title_final or filename,
            "folder": folder_final or "",
            "tags": [t["label"] for t in tags if t.get("label")],
            "created_at": created_at,
            "created_ts": created_ts,
            "transcription_status": transcription_status,
            "status": status_message,
            "auto_category": note_data.get("auto_category"),
            "auto_category_confidence": note_data.get("auto_category_confidence"),
            "auto_program": note_data.get("auto_program"),
            "auto_program_confidence": note_data.get("auto_program_confidence"),
        }
        if summary:
            response["summary"] = summary
            response["feedback"] = f"Snapshot: {summary}"
        elif transcription_status == "pending":
            response["feedback"] = "Snapshot: Transcription underway — I’ll circle back once it finishes."
        return response

    message = (
        transcription_form
        or str(
            (body or {}).get("message")
            or (body or {}).get("text")
            or (body or {}).get("body")
            or query_params.get("message")
            or query_params.get("text")
            or ""
        ).strip()
    )
    if not message:
        return Response(status_code=400, content="Missing message text")

    payload: dict = {
        "transcription": message,
        "title": title_value,
        "date": date_value,
        "folder": folder_value,
        "tags": tags,
    }

    try:
        result = await note_logic.create_note_from_text_payload(payload, include_summary=True)
        tags_resp = [
            t.get("label") for t in (result.get("tags") or []) if isinstance(t, dict) and t.get("label")
        ]
        folder_final = (result.get("folder") or "").strip()
        status_bits = [f"Saved “{result.get('title')}”"]
        if folder_final:
            status_bits.append(f"in folder “{folder_final}”")
        else:
            status_bits.append("to your uncategorized inbox")
        if tags_resp:
            shown = ", ".join(tags_resp[:3])
            if len(tags_resp) > 3:
                shown += ", …"
            status_bits.append(f"tags: {shown}")
        if result.get("auto_category"):
            status_bits.append(f"auto category: {result.get('auto_category')}")
        if result.get("auto_program"):
            status_bits.append(f"program: {result.get('auto_program')}")
        status_message = "; ".join(status_bits) + "."
        response = {
            "source": "telegram",
            "input_type": "text",
            "filename": result["filename"],
            "title": result.get("title"),
            "folder": folder_final,
            "tags": tags_resp,
            "created_at": result.get("created_at"),
            "created_ts": result.get("created_ts"),
            "summary": result.get("summary"),
            "status": status_message,
            "auto_category": result.get("auto_category"),
            "auto_category_confidence": result.get("auto_category_confidence"),
            "auto_program": result.get("auto_program"),
            "auto_program_confidence": result.get("auto_program_confidence"),
        }
        if result.get("summary"):
            response["feedback"] = f"Snapshot: {result['summary']}"
        return response
    except ValueError:
        return Response(status_code=400)
    except Exception as e:
        return {"error": str(e)}
