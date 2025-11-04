import asyncio
import logging
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, Response
from langchain_core.messages import HumanMessage

import config
import providers
import usage_log as usage
from core.note_logic import summarize_text_snippet, apply_classification

router = APIRouter()

NARRATIVES_DIR = config.NARRATIVES_DIR
NARRATIVE_META_DIR = os.path.join(NARRATIVES_DIR, "meta")
TRANSCRIPTS_DIR = config.TRANSCRIPTS_DIR


def _narrative_meta_path(filename: str) -> str:
    os.makedirs(NARRATIVE_META_DIR, exist_ok=True)
    return os.path.join(NARRATIVE_META_DIR, f"{filename}.json")


def _read_narrative_meta(filename: str) -> dict:
    try:
        p = _narrative_meta_path(filename)
        if os.path.exists(p):
            with open(p, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _write_narrative_meta(filename: str, data: dict) -> None:
    os.makedirs(NARRATIVE_META_DIR, exist_ok=True)
    p = _narrative_meta_path(filename)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data or {}, f, ensure_ascii=False)
    os.replace(tmp, p)


def _load_transcription(base_filename: str) -> Optional[dict]:
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
    if not os.path.exists(json_path):
        return None
    try:
        with open(json_path, "r") as jf:
            data = json.load(jf)
        return data
    except Exception:
        return None


@router.get("/api/narratives")
async def list_narratives():
    if not os.path.exists(NARRATIVES_DIR):
        os.makedirs(NARRATIVES_DIR)
    return [f for f in sorted(os.listdir(NARRATIVES_DIR)) if f.endswith(".txt")]


@router.get("/api/narratives/{filename}")
async def get_narrative(filename: str):
    path = os.path.join(NARRATIVES_DIR, filename)
    if not os.path.exists(path):
        return Response(status_code=404)
    with open(path, "r") as f:
        content = f.read()
    title = None
    try:
        meta_path = os.path.join(NARRATIVE_META_DIR, f"{filename}.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as mf:
                meta = json.load(mf)
            title = (meta or {}).get("title")
    except Exception:
        title = None
    return {"content": content, "title": title}


@router.delete("/api/narratives/{filename}")
async def delete_narrative(filename: str):
    path = os.path.join(NARRATIVES_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return Response(status_code=200)
    return Response(status_code=404)


@router.post("/api/narratives")
async def create_narrative_from_notes(request: Request):
    try:
        items = await request.json()
        if not isinstance(items, list):
            return Response(status_code=400)
        parts = []
        for it in items:
            name = (it or {}).get("filename")
            if not name or not isinstance(name, str):
                continue
            base = os.path.splitext(name)[0]
            data = _load_transcription(base) or {}
            title = data.get("title") or base
            text = data.get("transcription") or ""
            parts.append(f"# {title}\n\n{text}\n\n")
        if not parts:
            return Response(status_code=400)
        if not os.path.exists(NARRATIVES_DIR):
            os.makedirs(NARRATIVES_DIR)
        name = f"narrative-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        out = os.path.join(NARRATIVES_DIR, name)
        content = "\n".join(parts)
        with open(out, "w") as f:
            f.write(content)
        try:
            os.makedirs(NARRATIVE_META_DIR, exist_ok=True)
            title = None
            for ln in content.splitlines():
                s = (ln or "").strip()
                if not s:
                    continue
                if s.startswith("#"):
                    s = s.lstrip("#").strip()
                title = s
                break
            if title:
                try:
                    msg = HumanMessage(content=[{"type": "text", "text": (
                        "Return exactly one short title (5–8 words) for the narrative below. "
                        "Do not include quotes, bullets, markdown, or extra text. Output only the title on one line.\n\n"
                        + content[:4000]
                    )}])
                    resp, _ = await asyncio.to_thread(providers.invoke_google, [msg])
                    title_llm = providers.normalize_title_output(getattr(resp, "content", ""))
                    if title_llm:
                        title = title_llm
                except Exception:
                    try:
                        title = providers.title_with_openai(content[:4000]) or title
                    except Exception:
                        pass
            if not title:
                title = os.path.splitext(name)[0]
            with open(os.path.join(NARRATIVE_META_DIR, f"{name}.json"), "w") as mf:
                json.dump({"title": title}, mf, ensure_ascii=False)
        except Exception:
            pass
        return {"filename": name}
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/narratives/generate")
async def generate_narrative(request: Request):
    try:
        body = await request.json()
        items = (body or {}).get("items", [])
        extra_text = (body or {}).get("extra_text", "")
        provider_choice = ((body or {}).get("provider") or "auto").lower()
        model_override = (body or {}).get("model")
        temperature = float((body or {}).get("temperature") or 0.2)
        system = (body or {}).get("system")

        if not isinstance(items, list) or not items:
            return Response(status_code=400, content="Missing items")

        sources: List[Dict[str, Any]] = []
        for obj in items:
            fn = str((obj or {}).get("filename") or "").strip()
            if not fn:
                continue
            base = os.path.splitext(fn)[0]
            data = _load_transcription(base)
            if not data:
                continue
            transcription = data.get("transcription") or ""
            title = data.get("title") or base
            sources.append({
                "type": "note",
                "filename": fn,
                "title": title,
                "transcription": transcription,
                "language": data.get("language"),
            })

        if not sources:
            return Response(status_code=400, content="No valid notes to generate from")

        parts = ["You are an expert editor. Synthesize a cohesive, structured narrative from the provided notes and context. Focus on clarity, key insights, and concrete action items. Keep it concise and readable.\n\n"]
        parts.append("Context Notes:\n")
        dbg_sources: List[Dict[str, Any]] = []
        for idx, src in enumerate(sources, start=1):
            title = src.get("title") or src.get("filename")
            transcription = src.get("transcription") or ""
            date = (src.get("date") or "").strip()
            header = f"[{idx}] {date} — {title}" if date else f"[{idx}] {title}"
            parts.append(f"{header}\n{transcription}\n\n")
            dbg_sources.append({
                "kind": "note",
                "filename": src.get("filename"),
                "title": title,
                "date": date,
                "text_len": len(transcription),
                "text_preview": transcription[:40],
            })

        if extra_text:
            parts.append("\nAdditional Context:\n" + extra_text + "\n")
        if system:
            parts.append("\nSystem Instructions:\n" + system + "\n")
        parts.append("\nWrite the narrative now.")
        prompt_text = "\n".join(parts)

        try:
            logging.info("[gen] items=%s sources=%s", len(items), json.dumps(dbg_sources)[:2000])
            logging.info("[gen] prompt_head=%s", (prompt_text[:800] + ('…' if len(prompt_text) > 800 else '')))
        except Exception:
            pass

        provider_used = provider_choice
        model_used = model_override or (config.GOOGLE_MODEL if provider_choice != "openai" else config.OPENAI_NARRATIVE_MODEL)
        key_index = None
        content: Optional[str] = None

        if provider_choice in ("auto", "gemini"):
            try:
                message = HumanMessage(content=[{"type": "text", "text": prompt_text}])
                resp, key_index = await asyncio.to_thread(
                    providers.invoke_google,
                    [message],
                    model_override if provider_choice == "gemini" and model_override else None,
                )
                content = str(getattr(resp, "content", resp))
                provider_used = "gemini"
                model_used = model_override or config.GOOGLE_MODEL
            except Exception:
                if provider_choice == "gemini":
                    raise
                provider_used = "openai"
                model_used = model_override or config.OPENAI_NARRATIVE_MODEL
                content = providers.openai_chat([HumanMessage(content=prompt_text)], model=model_override, temperature=temperature)
        else:
            provider_used = "openai"
            model_used = model_override or config.OPENAI_NARRATIVE_MODEL
            content = providers.openai_chat([HumanMessage(content=prompt_text)], model=model_override, temperature=temperature)

        if not os.path.exists(NARRATIVES_DIR):
            os.makedirs(NARRATIVES_DIR)
        name = f"narrative-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        out = os.path.join(NARRATIVES_DIR, name)
        with open(out, "w") as f:
            f.write(content or "")

        transcription = content or ""
        summary = await summarize_text_snippet(transcription)
        meta = {"title": None, "summary": summary}
        apply_classification(meta, meta.get("title"), transcription)
        try:
            _write_narrative_meta(name, meta)
        except Exception:
            pass

        try:
            usage.log_usage(
                event="narrative",
                provider=provider_used,
                model=model_used,
                key_label=(
                    providers.key_label_from_index(key_index or 0)
                    if provider_used == "gemini"
                    else usage.OPENAI_LABEL
                ),
                status="success",
            )
        except Exception:
            pass

        return {"filename": name}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/narratives/thread/{filename}")
async def get_thread(filename: str):
    try:
        path = os.path.join(NARRATIVES_DIR, "threads.json")
        if not os.path.exists(path):
            return {"files": [filename], "index": 0}
        with open(path, "r") as f:
            data = json.load(f)
        mapping = data.get("map", {})
        thread_id = mapping.get(filename)
        if not thread_id:
            return {"files": [filename], "index": 0}
        for thread in data.get("threads", []):
            if thread.get("id") == thread_id:
                files = thread.get("files", [])
                try:
                    index = files.index(filename)
                except ValueError:
                    index = 0
                return {"files": files, "index": index}
        return {"files": [filename], "index": 0}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/formats")
async def list_formats():
    os.makedirs(config.FORMATS_DIR, exist_ok=True)
    out = []
    for fn in sorted(os.listdir(config.FORMATS_DIR)):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(config.FORMATS_DIR, fn), "r") as f:
                    data = json.load(f)
                fid = data.get("id") or os.path.splitext(fn)[0]
                out.append({
                    "id": fid,
                    "title": data.get("title") or fid,
                    "prompt": data.get("prompt") or "",
                })
            except Exception:
                continue
    return out


@router.post("/api/formats")
async def create_or_update_format(request: Request):
    try:
        body = await request.json()
        title = (body or {}).get("title")
        prompt = (body or {}).get("prompt")
        fid = (body or {}).get("id")
        if not title or not prompt:
            return Response(status_code=400)
        os.makedirs(config.FORMATS_DIR, exist_ok=True)
        if not fid:
            fid = uuid.uuid4().hex[:12]
        path = os.path.join(config.FORMATS_DIR, f"{fid}.json")
        with open(path, "w") as f:
            json.dump({"id": fid, "title": title, "prompt": prompt}, f, ensure_ascii=False)
        return {"id": fid}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/api/formats/{fid}")
async def delete_format(fid: str):
    try:
        path = os.path.join(config.FORMATS_DIR, f"{fid}.json")
        if os.path.exists(path):
            os.remove(path)
            return Response(status_code=200)
        return Response(status_code=404)
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/narratives/list")
async def list_narratives_meta():
    os.makedirs(NARRATIVES_DIR, exist_ok=True)
    files = [f for f in sorted(os.listdir(NARRATIVES_DIR)) if f.endswith(".txt")]
    out = []
    for fn in files:
        meta = _read_narrative_meta(fn)
        out.append({
            "filename": fn,
            "title": meta.get("title"),
            "folder": (meta.get("folder") or "").strip(),
        })
    return out


@router.patch("/api/narratives/{filename}/folder")
async def set_narrative_folder(filename: str, request: Request):
    try:
        body = await request.json()
        folder = str((body or {}).get("folder") or "").strip()
        meta = _read_narrative_meta(filename)
        meta["folder"] = folder
        _write_narrative_meta(filename, meta)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/narratives/folders")
async def list_narrative_folders():
    os.makedirs(NARRATIVES_DIR, exist_ok=True)
    files = [f for f in sorted(os.listdir(NARRATIVES_DIR)) if f.endswith(".txt")]
    counts: Dict[str, int] = {}
    for fn in files:
        try:
            meta = _read_narrative_meta(fn)
            folder = (meta.get("folder") or "").strip()
            if folder:
                counts[folder] = counts.get(folder, 0) + 1
        except Exception:
            continue
    return [{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: kv[0].lower())]
