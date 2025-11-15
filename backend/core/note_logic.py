from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, UploadFile
from langchain_core.messages import HumanMessage

import categorizer
import config
import note_store as _note_store
import providers
from services import transcribe_and_save
from core.programs import load_programs_registry

logger = logging.getLogger(__name__)


async def summarize_text_snippet(text: str) -> Optional[str]:
    snippet = (text or "").strip()
    if not snippet:
        return None
    try:
        prompt = HumanMessage(
            content=[{
                "type": "text",
                "text": (
                    "Provide a concise 1-2 sentence recap of the following note. "
                    "Highlight decisions, owners, or next steps if present. "
                    "Keep it under 240 characters.\n\n" + snippet[:4000]
                )
            }]
        )
        resp, _ = await asyncio.to_thread(providers.invoke_google, [prompt])
        summary = str(getattr(resp, "content", "")).strip()
        if summary:
            summary = " ".join(summary.split())
            if len(summary) > 260:
                summary = summary[:257].rstrip() + "…"
            return summary
    except Exception:
        try:
            summary = providers.openai_chat([
                HumanMessage(
                    content=(
                        "Summarize in <=240 characters. Mention key decisions or follow-ups.\n\n" + snippet[:4000]
                    )
                )
            ], temperature=0.2)
            summary = str(summary or "").strip()
            if summary:
                summary = " ".join(summary.split())
                if len(summary) > 260:
                    summary = summary[:257].rstrip() + "…"
                return summary
        except Exception:
            pass
    return None


def apply_classification(
    note_data: Dict[str, Any],
    title: Optional[str],
    transcription: str,
) -> Optional[categorizer.CategorizationResult]:
    try:
        programs = load_programs_registry()
        classification = categorizer.categorize_note(transcription, title, programs)
    except Exception:
        return None
    note_data["auto_category"] = classification.domain
    note_data["auto_category_confidence"] = classification.confidence
    note_data["auto_category_rationale"] = classification.rationale
    if classification.program:
        note_data["auto_program"] = classification.program
    if classification.program_confidence is not None:
        note_data["auto_program_confidence"] = classification.program_confidence
    if classification.program_rationale:
        note_data["auto_program_rationale"] = classification.program_rationale
    logger.info(
        "[categorize] note=%s domain=%s program=%s conf=%.2f",
        note_data.get("filename"),
        classification.domain,
        classification.program,
        classification.confidence,
    )
    return classification


async def create_note_from_text_payload(body: dict, include_summary: bool = False) -> dict:
    transcription = str((body or {}).get("transcription") or "").strip()
    if not transcription:
        raise ValueError("Missing transcription")
    title = str((body or {}).get("title") or "").strip()
    date_override = str((body or {}).get("date") or "").strip()
    folder = str((body or {}).get("folder") or "").strip()
    tags_raw = (body or {}).get("tags") or []

    tags: list[dict] = []
    if isinstance(tags_raw, str):
        tags = [{"label": t.strip()} for t in tags_raw.split(",") if t.strip()]
    elif isinstance(tags_raw, dict):
        for key, value in tags_raw.items():
            label = str(key or '').strip()
            if not label:
                continue
            color = value.get("color") if isinstance(value, dict) else None
            tags.append({"label": label, "color": color})
    elif isinstance(tags_raw, list):
        for item in tags_raw:
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

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    nid = f"text-{stamp}-{uuid.uuid4().hex[:6]}"
    pseudo_filename = f"{nid}.txt"

    if not title:
        try:
            title_message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "Return exactly one short title (5–8 words) for the transcription below. "
                            "Use the same language as the transcription. Do not include quotes, bullets, markdown, or any extra text. "
                            "Output only the title on a single line.\n\n" + transcription
                        ),
                    },
                ]
            )
            title_response, _ = await asyncio.to_thread(
                providers.invoke_google, [title_message]
            )
            title = providers.normalize_title_output(getattr(title_response, "content", ""))
        except Exception:
            try:
                title = providers.title_with_openai(transcription)
            except Exception:
                words = (transcription or '').strip().split()
                title = ' '.join(words[:8]) if words else 'Text Note'

    now = datetime.now()
    data = {
        "filename": pseudo_filename,
        "title": (title or '').strip() or 'Text Note',
        "transcription": transcription,
        "date": date_override or datetime.now().strftime('%Y-%m-%d'),
        "created_at": now.isoformat(),
        "created_ts": int(now.timestamp() * 1000),
        "length_seconds": None,
        "topics": _note_store.infer_topics(transcription, title or None),
        "language": _note_store.infer_language(transcription, title or None),
        "folder": folder,
        "tags": [{"label": t["label"], "color": t.get("color")} for t in tags if t.get("label")],
    }

    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
    classification = apply_classification(data, title, transcription)
    summary = await summarize_text_snippet(transcription) if include_summary else None

    with open(os.path.join(config.TRANSCRIPTS_DIR, f"{nid}.json"), 'w') as jf:
        json.dump(data, jf, ensure_ascii=False)

    result: Dict[str, Any] = {
        "filename": pseudo_filename,
        "title": data["title"],
        "folder": data["folder"] or "",
        "tags": data["tags"],
        "created_at": data["created_at"],
        "created_ts": data["created_ts"],
    }
    if summary:
        result["summary"] = summary
    if classification is not None:
        result["auto_category"] = data.get("auto_category")
        result["auto_category_confidence"] = data.get("auto_category_confidence")
        result["auto_program"] = data.get("auto_program")
        result["auto_program_confidence"] = data.get("auto_program_confidence")
    return result


async def process_audio_upload(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    date: Optional[str] = None,
    place: Optional[str] = None,
    folder: Optional[str] = None,
) -> Dict[str, str]:
    os.makedirs(config.VOICE_NOTES_DIR, exist_ok=True)

    ct = file.content_type or ""
    ct_lower = ct.lower()
    orig_name = (file.filename or "")
    name_ext = os.path.splitext(orig_name)[1].lstrip(".").lower()

    is_video = False
    if ct.startswith("video/") or name_ext in ("mkv", "mp4", "mov", "avi"):
        is_video = True

    needs_transcode = False
    source_ext: Optional[str] = None
    target_ext: Optional[str] = None
    upload_ext = name_ext or None

    if not is_video:
        if "webm" in ct_lower or name_ext == "webm":
            source_ext = "webm"
            target_ext = "m4a"
            needs_transcode = True
        elif "ogg" in ct_lower or name_ext == "ogg":
            source_ext = "ogg"
            target_ext = "m4a"
            needs_transcode = True
        elif ("m4a" in ct_lower) or ("mp4" in ct_lower) or ("aac" in ct_lower) or name_ext in ("m4a", "mp4", "mp4a", "aac"):
            source_ext = "m4a"
            target_ext = "m4a"
            needs_transcode = name_ext not in ("m4a", "mp4", "mp4a", "aac")
        elif "mp3" in ct_lower or name_ext == "mp3":
            source_ext = "mp3"
            target_ext = "mp3"
        else:
            source_ext = name_ext or "wav"
            target_ext = "wav"
            if "mp4" in ct_lower or "aac" in ct_lower:
                source_ext = "m4a"
                target_ext = "m4a"
                needs_transcode = True
    else:
        source_ext = name_ext or "mkv"
        target_ext = "m4a"
        needs_transcode = True

    ext = (target_ext or source_ext or "m4a").lower()
    source_ext = (source_ext or "").lower() or None

    logger.info(
        "Incoming note upload: original_name=%s upload_ext=%s content_type=%s source_ext=%s -> target_ext=%s (transcode=%s)",
        orig_name,
        upload_ext or "unknown",
        ct or "unknown",
        source_ext or "unknown",
        ext,
        needs_transcode,
    )

    stored_mime = {
        "m4a": "audio/mp4",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "webm": "audio/webm",
    }.get(ext, f"audio/{ext}")
    metadata_fields: Dict[str, Any] = {
        "audio_format": ext,
        "stored_mime": stored_mime,
        "original_format": source_ext or ext,
        "transcoded": bool(needs_transcode),
    }
    if upload_ext:
        metadata_fields["upload_extension"] = upload_ext
    if needs_transcode and source_ext and source_ext != ext:
        metadata_fields["transcoded_from"] = source_ext
    if ct:
        metadata_fields["content_type"] = ct
    if needs_transcode or ext in ("m4a", "wav"):
        if ext == "m4a":
            metadata_fields.setdefault("sample_rate_hz", 44100)
        elif ext == "wav":
            metadata_fields.setdefault("sample_rate_hz", 16000)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{uuid.uuid4().hex[:6]}.{ext}"
    file_path = os.path.join(config.VOICE_NOTES_DIR, filename)

    upload_bytes = file.file.read()
    if needs_transcode:
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + (source_ext or "tmp")) as tmp:
            tmp.write(upload_bytes)
            tmp_path = tmp.name
        try:
            cmd = ["ffmpeg", "-y", "-i", tmp_path]
            if ext == "m4a":
                cmd += ["-vn", "-ac", "1", "-ar", "44100", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", file_path]
            elif ext == "wav":
                cmd += ["-vn", "-ac", "1", "-ar", "16000", file_path]
            else:
                cmd += ["-vn", file_path]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            raise RuntimeError(f"Failed to normalize audio: {e}")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    else:
        with open(file_path, "wb") as buffer:
            buffer.write(upload_bytes)

    try:
        base_filename = os.path.splitext(filename)[0]
        payload_min = _note_store.build_note_payload(
            filename, base_filename, "", metadata_fields, include_length=False
        )
        if folder:
            payload_min["folder"] = (folder or "").strip()
        _note_store.save_note_json(base_filename, payload_min)
        try:
            _note_store.ensure_placeholder_note(filename)
        except Exception:
            pass
    except Exception:
        pass

    background_tasks.add_task(transcribe_and_save, file_path)
    return {"filename": filename, "message": "File upload successful, transcription started."}
