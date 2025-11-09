from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, File, Form, Request, Response, UploadFile
from starlette.datastructures import Headers

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


def _ensure_tag(tags: list[dict], label: str) -> list[dict]:
    if not label:
        return tags
    target = label.strip().lower()
    if not target:
        return tags
    for tag in tags:
        existing = str((tag.get("label") or "")).strip().lower()
        if existing == target:
            return tags
    tags.append({"label": label})
    return tags


def _visible_tag_labels(value: object) -> list[str]:
    labels: list[str] = []
    if not value:
        return labels
    seen: set[str] = set()

    def _add(label: str) -> None:
        normalized = label.strip()
        if not normalized:
            return
        lowered = normalized.lower()
        if lowered == "telegram":
            return
        if lowered in seen:
            return
        seen.add(lowered)
        labels.append(normalized)

    if isinstance(value, str):
        if value.strip().startswith("[") or value.strip().startswith("{"):
            try:
                parsed = json.loads(value)
                labels.extend(_visible_tag_labels(parsed))
                return labels
            except Exception:
                pass
        for token in value.split(","):
            _add(token)
        return labels
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, dict) and item.get("label"):
                _add(str(item.get("label") or ""))
            else:
                _add(str(key or ""))
        return labels
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                label = item.get("label") or item.get("name") or item.get("title")
                if label is not None:
                    _add(str(label))
            else:
                _add(str(item or ""))
        return labels
    _add(str(value or ""))
    return labels


def _build_status_message(
    note_data: Dict[str, Any],
    filename: str,
    title: Optional[str],
    tags: list[str],
    transcription_status: str,
) -> str:
    display_title = title or filename
    status_bits = [f"Saved “{display_title}”"]
    if tags:
        shown = ", ".join(tags[:3])
        if len(tags) > 3:
            shown += ", …"
        status_bits.append(f"tags: {shown}")

    if transcription_status == "failed":
        status_bits.append("transcription failed – retry from the app")

    return "; ".join(status_bits) + "."


async def _send_followup_when_ready(
    chat_id: int,
    message_id: Optional[int],
    filename: Optional[str],
    fallback_tags: Optional[list[dict]] = None,
) -> None:
    if not filename:
        logger.warning("[telegram-webhook] follow-up skipped: missing filename")
        return

    base_name = os.path.splitext(filename)[0]
    json_path = os.path.join(config.TRANSCRIPTS_DIR, f"{base_name}.json")
    deadline = time.time() + 300  # wait up to 5 minutes

    try:
        while time.time() < deadline:
            try:
                if not os.path.exists(json_path):
                    await asyncio.sleep(4)
                    continue
                with open(json_path, "r") as jf:
                    note_data = json.load(jf)
            except Exception:
                await asyncio.sleep(4)
                continue

            transcription_text = str(note_data.get("transcription") or "").strip()
            if transcription_text and transcription_text != "Transcription failed.":
                title_final = str(note_data.get("title") or "").strip() or os.path.splitext(filename)[0]
                folder_final = str(note_data.get("folder") or "").strip()
                visible_tags = _visible_tag_labels(note_data.get("tags"))
                if not visible_tags and fallback_tags:
                    visible_tags = _visible_tag_labels(fallback_tags)

                summary = note_data.get("telegram_summary") or note_data.get("summary")
                updated = False
                if not summary:
                    summary = await note_logic.summarize_text_snippet(transcription_text)
                    if summary:
                        note_data["telegram_summary"] = summary
                        updated = True

                classification = note_logic.apply_classification(
                    note_data, title_final, transcription_text
                )
                if classification is not None:
                    updated = True

                if updated:
                    try:
                        with open(json_path, "w") as jf:
                            json.dump(note_data, jf, ensure_ascii=False)
                    except Exception:
                        pass

                status_message = _build_status_message(
                    note_data,
                    filename,
                    title_final,
                    visible_tags,
                    "complete",
                )
                await _telegram_send_message(chat_id, status_message, reply_to=message_id)
                return

            if transcription_text == "Transcription failed.":
                await _telegram_send_message(
                    chat_id,
                    "Transcription failed for that note — you can retry from the app or send it again.",
                    reply_to=message_id,
                )
                return

            await asyncio.sleep(5)
    except Exception:
        logger.exception("Error sending Telegram follow-up for filename=%s", filename)
        await _telegram_send_message(
            chat_id,
            "I hit a snag finishing that note. You can retry the transcription from the app.",
            reply_to=message_id,
        )
        return

    await _telegram_send_message(
        chat_id,
        "Still waiting on transcription — I’ll update you as soon as it’s ready.",
        reply_to=message_id,
    )


async def _handle_audio_note(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    folder_value: str,
    tags: list[dict],
    date_value: str | None = None,
) -> Dict[str, Any]:
    try:
        upload_result = await note_logic.process_audio_upload(
            file=file,
            background_tasks=background_tasks,
            date=date_value or None,
            place=None,
            folder=folder_value or None,
        )
    except RuntimeError as exc:
        return {"error": f"Upload failed: {exc}"}
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
            updated = False
            if summary:
                note_data["telegram_summary"] = summary
                updated = True
            classification = note_logic.apply_classification(note_data, title_final, transcription_text)
            if classification is not None:
                updated = True
            if updated:
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

    summary = note_data.get("telegram_summary") or summary
    folder_final = folder_value or str(note_data.get("folder") or "").strip()
    visible_tags = _visible_tag_labels(note_data.get("tags"))
    if not visible_tags and tags:
        visible_tags = _visible_tag_labels(tags)
    status_message = _build_status_message(
        note_data,
        filename,
        title_final,
        visible_tags,
        transcription_status,
    )

    response: Dict[str, Any] = {
        "source": "telegram",
        "input_type": "audio",
        "filename": filename,
        "title": title_final or filename,
        "folder": folder_final or "",
        "tags": visible_tags,
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
    return response


async def _handle_text_note(
    message: str,
    title_value: str,
    date_value: str,
    folder_value: str,
    tags: list[dict],
) -> Dict[str, Any]:
    payload: dict = {
        "transcription": message,
        "title": title_value,
        "date": date_value,
        "folder": folder_value,
        "tags": tags,
    }

    result = await note_logic.create_note_from_text_payload(payload, include_summary=True)
    tags_resp = _visible_tag_labels(result.get("tags"))
    folder_final = (result.get("folder") or "").strip()
    status_message = _build_status_message(
        result,
        result["filename"],
        result.get("title"),
        tags_resp,
        "complete",
    )
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
    return response


def _telegram_bot_base() -> str:
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("Telegram bot token is not configured")
    return f"https://api.telegram.org/bot{token}"


def _telegram_file_base() -> str:
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("Telegram bot token is not configured")
    return f"https://api.telegram.org/file/bot{token}"


async def _telegram_send_message(
    chat_id: int,
    text: str,
    reply_to: Optional[int] = None,
) -> None:
    if not text:
        return
    try:
        base = _telegram_bot_base()
    except RuntimeError as exc:
        logger.warning("telegram send skipped: %s", exc)
        return
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_to is not None:
        payload["reply_to_message_id"] = reply_to
        payload["allow_sending_without_reply"] = True
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{base}/sendMessage", json=payload)
            if resp.status_code >= 400:
                logger.warning(
                    "telegram send failed status=%s body=%s",
                    resp.status_code,
                    resp.text[:256],
                )
    except Exception:
        logger.exception("Error sending Telegram message")


async def _telegram_download_file(file_id: str) -> Tuple[bytes, str]:
    base = _telegram_bot_base()
    file_base = _telegram_file_base()
    async with httpx.AsyncClient(timeout=30) as client:
        meta_resp = await client.get(f"{base}/getFile", params={"file_id": file_id})
        meta_resp.raise_for_status()
        meta_data = meta_resp.json()
        if not meta_data.get("ok"):
            raise RuntimeError(f"telegram getFile failed: {meta_data}")
        result = meta_data.get("result") or {}
        file_path = result.get("file_path")
        if not file_path:
            raise RuntimeError("telegram getFile missing file_path")
        download_resp = await client.get(f"{file_base}/{file_path}")
        download_resp.raise_for_status()
        return download_resp.content, os.path.basename(file_path)


@router.post("/api/integrations/telegram/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram webhook received but TELEGRAM_BOT_TOKEN is not configured")
        return Response(status_code=503, content="Telegram bot not configured")

    secret = config.TELEGRAM_WEBHOOK_SECRET
    header_secret = request.headers.get("x-telegram-bot-api-secret-token")
    if secret and header_secret != secret:
        logger.warning(
            "Telegram webhook secret mismatch; header_present=%s",
            bool(header_secret),
        )
        return Response(status_code=401)

    try:
        update = await request.json()
    except Exception:
        return Response(status_code=400)
    else:
        try:
            logger.info(
                "[telegram-webhook] update=%s",
                json.dumps(update, ensure_ascii=False)[:4000],
            )
        except Exception:
            logger.info("[telegram-webhook] received update (unable to serialize)")

    message = (update.get("message") or update.get("edited_message") or {})
    if not message:
        return {"ok": True}

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return {"ok": True}

    message_id = message.get("message_id")
    text = str(message.get("text") or "").strip()
    caption = str(message.get("caption") or "").strip()
    payload_kind = "text" if text else "caption" if caption else None

    if text.startswith("/start"):
        await _telegram_send_message(
            chat_id,
            text=(
                "Hi! I’m Narrative Hero. Send me a voice memo or text and I’ll capture it, "
                "transcribe it, and keep it organized for you."
            ),
            reply_to=message_id,
        )
        return {"ok": True}

    folder_value = ""
    date_value = ""
    tags = _ensure_tag([], "telegram")

    media_key_used: str | None = None
    for key in ("voice", "audio", "video_note", "video", "document"):
        if message.get(key):
            media_key_used = key
            break

    logger.info(
        "[telegram-webhook] chat_id=%s message_id=%s payload=%s media_key=%s has_document=%s",
        chat_id,
        message_id,
        payload_kind,
        media_key_used,
        bool(message.get("document")),
    )

    try:
        if text:
            result = await _handle_text_note(
                message=text,
                title_value="",
                date_value=date_value,
                folder_value=folder_value,
                tags=tags,
            )
        else:
            file_info: Optional[Dict[str, Any]] = message.get(media_key_used) if media_key_used else None
            if not file_info:
                for key in ("voice", "audio", "video_note", "video", "document"):
                    if message.get(key):
                        file_info = message[key]
                        media_key_used = key
                        break
            if not file_info:
                await _telegram_send_message(
                    chat_id,
                    text="I can only process text messages or voice/audio notes right now.",
                    reply_to=message_id,
                )
                return {"ok": True}
            file_id = file_info.get("file_id")
            if not file_id:
                await _telegram_send_message(
                    chat_id,
                    text="I couldn't find the audio file to download.",
                    reply_to=message_id,
                )
                return {"ok": True}

            try:
                file_bytes, downloaded_name = await _telegram_download_file(file_id)
            except Exception as exc:
                logger.exception("Error downloading Telegram file")
                await _telegram_send_message(
                    chat_id,
                    text="Downloading the audio from Telegram failed. Please try again.",
                    reply_to=message_id,
                )
                return {"ok": True}

            filename = file_info.get("file_name") or downloaded_name or f"{file_id}.ogg"
            mime_type = file_info.get("mime_type") or "application/octet-stream"
            buffer = io.BytesIO(file_bytes)
            buffer.seek(0)
            headers = Headers({"content-type": mime_type}) if mime_type else None
            upload = UploadFile(file=buffer, filename=filename, headers=headers)
            logger.info(
                "[telegram-webhook] downloading media chat_id=%s message_id=%s filename=%s mime=%s size_bytes=%s",
                chat_id,
                message_id,
                filename,
                mime_type,
                len(file_bytes),
            )
            try:
                result = await _handle_audio_note(
                    file=upload,
                    background_tasks=background_tasks,
                    folder_value=folder_value,
                    tags=tags,
                    date_value=date_value or None,
                )
            finally:
                await upload.close()
        if result.get("error"):
            await _telegram_send_message(
                chat_id,
                text=f"That didn’t work: {result['error']}",
                reply_to=message_id,
            )
            return {"ok": True}

        logger.info(
            "[telegram-webhook] processed chat_id=%s message_id=%s filename=%s input_type=%s transcription_status=%s",
            chat_id,
            message_id,
            result.get("filename"),
            result.get("input_type"),
            result.get("transcription_status"),
        )

        transcription_status = result.get("transcription_status") or "complete"
        if transcription_status == "pending":
            asyncio.create_task(
                _send_followup_when_ready(
                    chat_id,
                    message_id,
                    result.get("filename"),
                    tags if isinstance(tags, list) else None,
                )
            )
        else:
            status = result.get("status")
            if status:
                await _telegram_send_message(
                    chat_id,
                    text=status,
                    reply_to=message_id,
                )
    except Exception:
        logger.exception("Unhandled error processing Telegram webhook update")
        await _telegram_send_message(
            chat_id,
            text="Something broke while saving that note. I’ll keep an eye on it.",
            reply_to=message_id,
        )
    return {"ok": True}


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
    shared_token = getattr(config, "TELEGRAM_INGEST_TOKEN", None)
    provided_token = (
        request.headers.get("x-webhook-token")
        or request.headers.get("x-telegram-token")
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
        logger.info(
            "[telegram-ingest] non-JSON body received; query=%s has_file=%s",
            dict(request.query_params),
            file is not None,
        )
    else:
        try:
            logger.info(
                "[telegram-ingest] json body=%s query=%s has_file=%s",
                json.dumps(body, ensure_ascii=False)[:4000],
                dict(request.query_params),
                file is not None,
            )
        except Exception:
            logger.info(
                "[telegram-ingest] received request (unable to serialize body); query=%s has_file=%s",
                dict(request.query_params),
                file is not None,
            )

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
    tags = _ensure_tag(tags, "telegram")

    if file is not None:
        response = await _handle_audio_note(
            file=file,
            background_tasks=background_tasks,
            folder_value=folder_value,
            tags=tags,
            date_value=date_value or None,
        )
        if response.get("error"):
            return response
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

    try:
        return await _handle_text_note(
            message=message,
            title_value=title_value,
            date_value=date_value,
            folder_value=folder_value,
            tags=tags,
        )
    except ValueError:
        return Response(status_code=400)
    except Exception as e:
        return {"error": str(e)}
