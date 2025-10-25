import logging

# Silence verbose loggers
logging.basicConfig(level=logging.INFO)
loggers_to_silence = [
    "google.generativeai",
    "langchain",
    "langchain_core",
    "langchain_google_genai",
]
for logger_name in loggers_to_silence:
    # Use ERROR to reduce noisy quota retry warnings
    logging.getLogger(logger_name).setLevel(logging.ERROR)

from fastapi import FastAPI, File, UploadFile, Form, Response, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from services import get_notes, transcribe_and_save
from models import TagsUpdate, FolderUpdate
from utils import on_startup
import uvicorn
import os
import json
from datetime import datetime
import uuid
import asyncio
import tempfile
import subprocess
import glob
import time
from langchain_core.messages import HumanMessage
import providers
import note_store as _ns
import config
import note_store as _note_store

app = FastAPI()

# Configure CORS to allow requests from the SvelteKit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(config, "ALLOWED_ORIGINS", [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
    ]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use centralized config paths, but keep module vars for tests to monkeypatch
VOICE_NOTES_DIR = config.VOICE_NOTES_DIR
TRANSCRIPTS_DIR = config.TRANSCRIPTS_DIR
NARRATIVES_DIR = config.NARRATIVES_DIR
NARRATIVE_META_DIR = os.path.join(NARRATIVES_DIR, 'meta')
FORMATS_DIR = getattr(config, 'FORMATS_DIR', os.path.join(config.STORAGE_DIR, 'formats'))

# Mount static files directory for voice notes
app.mount("/voice_notes", StaticFiles(directory=VOICE_NOTES_DIR, check_dir=False), name="voice_notes")

@app.on_event("startup")
async def startup_event():
    await on_startup()

## LangHero scenario route removed from Narrative Hero

@app.get("/api/notes")
async def read_notes():
    """API endpoint to retrieve all notes."""
    return get_notes()

@app.post("/api/notes")
async def create_note(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    date: str = Form(None),
    place: str = Form(None),
    folder: str = Form(None)
):
    """API endpoint to upload a new note."""
    os.makedirs(VOICE_NOTES_DIR, exist_ok=True)

    ct = file.content_type or ''
    ct_lower = ct.lower()
    orig_name = (file.filename or '')
    name_ext = os.path.splitext(orig_name)[1].lstrip('.').lower()

    # Detect video uploads (we only keep/extract audio)
    is_video = False
    if ct.startswith('video/') or name_ext in ('mkv', 'mp4', 'mov', 'avi'):
        is_video = True

    needs_transcode = False
    source_ext = None
    target_ext = None

    upload_ext = name_ext or None

    if not is_video:
        if 'webm' in ct_lower or name_ext == 'webm':
            source_ext = 'webm'
            target_ext = 'm4a'
            needs_transcode = True
        elif 'ogg' in ct_lower or name_ext == 'ogg':
            source_ext = 'ogg'
            target_ext = 'm4a'
            needs_transcode = True
        elif ('m4a' in ct_lower) or ('mp4' in ct_lower) or ('aac' in ct_lower) or name_ext in ('m4a', 'mp4', 'mp4a', 'aac'):
            source_ext = 'm4a'
            target_ext = 'm4a'
            # Re-encode if uploaded extension wasn't already m4a/mp4
            needs_transcode = name_ext not in ('m4a', 'mp4', 'mp4a', 'aac')
        elif 'mp3' in ct_lower or name_ext == 'mp3':
            source_ext = 'mp3'
            target_ext = 'mp3'
        else:
            source_ext = name_ext or 'wav'
            target_ext = 'wav'
            # If the declared content-type suggests mp4 but filename is wav, prefer converting to m4a
            if 'mp4' in ct_lower or 'aac' in ct_lower:
                source_ext = 'm4a'
                target_ext = 'm4a'
                needs_transcode = True
    else:
        # Video inputs → convert audio track to AAC (m4a) for broad compatibility
        source_ext = (name_ext or 'mkv')
        target_ext = 'm4a'
        needs_transcode = True

    ext = (target_ext or source_ext or 'm4a')
    ext = (ext or 'm4a').lower()
    source_ext = (source_ext or '').lower() or None
    logging.info(
        "Incoming note upload: original_name=%s upload_ext=%s content_type=%s source_ext=%s -> target_ext=%s (transcode=%s)",
        orig_name,
        upload_ext or "unknown",
        ct or "unknown",
        source_ext or "unknown",
        ext,
        needs_transcode,
    )
    stored_mime = {
        'm4a': 'audio/mp4',
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'webm': 'audio/webm',
    }.get(ext, f"audio/{ext}")
    metadata_fields = {
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
    if needs_transcode or ext in ('m4a', 'wav'):
        if ext == 'm4a':
            metadata_fields.setdefault("sample_rate_hz", 44100)
        elif ext == 'wav':
            metadata_fields.setdefault("sample_rate_hz", 16000)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{uuid.uuid4().hex[:6]}.{ext}"
    file_path = os.path.join(VOICE_NOTES_DIR, filename)

    # Read entire upload once (handles both audio and video)
    upload_bytes = file.file.read()
    if needs_transcode:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.' + (source_ext or 'tmp')) as tmp:
            tmp.write(upload_bytes)
            tmp_path = tmp.name
        try:
            cmd = ['ffmpeg', '-y', '-i', tmp_path]
            if ext == 'm4a':
                cmd += ['-vn', '-ac', '1', '-ar', '44100', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', file_path]
            elif ext == 'wav':
                cmd += ['-vn', '-ac', '1', '-ar', '16000', file_path]
            else:
                cmd += ['-vn', file_path]
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
            return Response(status_code=400, content=f"Failed to normalize audio: {e}")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    else:
        with open(file_path, "wb") as buffer:
            buffer.write(upload_bytes)
    
    # If a folder is provided, create or update a minimal JSON immediately so
    # the note appears under the selected folder before transcription completes.
    try:
        base_filename = os.path.splitext(filename)[0]
        import note_store as _ns
        # Minimal payload: use base as a placeholder title, empty transcription
        payload_min = _ns.build_note_payload(filename, base_filename, "", metadata_fields)
        if folder:
            payload_min["folder"] = (folder or "").strip()
        _ns.save_note_json(base_filename, payload_min)
    except Exception:
        # Non-fatal; background task will create JSON later
        pass

    # Start transcription and title generation in the background
    print(f"File saved: {filename}. Adding transcription to background tasks.")
    background_tasks.add_task(transcribe_and_save, file_path)
    
    return {"filename": filename, "message": "File upload successful, transcription started."}

@app.post("/api/notes/{filename}/retry")
async def retry_note(background_tasks: BackgroundTasks, filename: str):
    """Manually trigger reprocessing (transcribe/title) for a specific note."""
    file_path = os.path.join(VOICE_NOTES_DIR, filename)
    if not os.path.exists(file_path):
        return Response(status_code=404)
    background_tasks.add_task(transcribe_and_save, file_path)
    return {"status": "queued"}

@app.delete("/api/notes/{filename}")
async def delete_note(filename: str):
    """API endpoint to delete a note."""
    file_path = os.path.join(VOICE_NOTES_DIR, filename)
    base_filename = os.path.splitext(filename)[0]
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
    legacy_txt_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.txt")
    deleted_any = False
    # Delete audio file if present
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            deleted_any = True
        except Exception:
            pass
    # Always attempt to delete associated JSON (and legacy txt) even if audio missing
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

_MODELS_CACHE: dict[str, tuple[float, list[str]]] = {}

def _cache_set(key: str, values: list[str], ttl: float = 600.0) -> list[str]:
    _MODELS_CACHE[key] = (time.time() + ttl, values)
    return values

def _cache_get(key: str) -> list[str] | None:
    exp_vals = _MODELS_CACHE.get(key)
    if not exp_vals:
        return None
    exp, vals = exp_vals
    if time.time() > exp:
        _MODELS_CACHE.pop(key, None)
        return None
    return vals

def _list_openai_latest() -> list[str]:
    cached = _cache_get("openai")
    if cached is not None:
        return cached
    ids: list[str] = []
    try:
        from openai import OpenAI
        if not getattr(config, 'OPENAI_API_KEY', None):
            raise RuntimeError('no openai key')
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        # Some servers paginate; keep it simple
        resp = client.models.list()
        all_ids = [getattr(m, 'id', None) or (m.get('id') if isinstance(m, dict) else None) for m in getattr(resp, 'data', [])]
        all_ids = [str(x) for x in all_ids if x]
        # Choose latest big (pro) and small (mini)
        prefer_pro = ["gpt-4.1", "gpt-4o"]
        prefer_mini = ["gpt-4.1-mini", "gpt-4o-mini"]
        lower_set = {str(x).lower() for x in all_ids}
        picks: list[str] = []
        for p in prefer_pro:
            if p.lower() in lower_set:
                picks.append(p); break
        for p in prefer_mini:
            if p.lower() in lower_set:
                # avoid duplicate if names collide
                if not picks or picks[-1].lower() != p.lower():
                    picks.append(p)
                break
        if not picks:
            # Reasonable defaults if list empty
            picks = [getattr(config, "OPENAI_NARRATIVE_MODEL", "gpt-4o"), "gpt-4.1-mini"]
        ids = picks
    except Exception:
        # Fallback to minimal curated list (pro + mini)
        ids = [getattr(config, "OPENAI_NARRATIVE_MODEL", "gpt-4o"), "gpt-4.1-mini"]
    # Dedup while preserving order
    seen: set[str] = set(); out: list[str] = []
    for x in ids:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return _cache_set("openai", out)

def _list_gemini_latest() -> list[str]:
    cached = _cache_get("gemini")
    if cached is not None:
        return cached
    ids: list[str] = []
    try:
        # Prefer google-generativeai if available for catalog listing
        import google.generativeai as genai
        if not config.collect_google_api_keys():
            raise RuntimeError('no gemini key')
        genai.configure(api_key=config.collect_google_api_keys()[0])
        models = list(genai.list_models())
        avail: set[str] = set()
        for m in models:
            mid = getattr(m, 'name', '') or getattr(m, 'model', '') or ''
            s = str(mid).split('/')[-1].lower()  # some return full resource names
            if s.startswith('gemini-'):
                avail.add(s)
        # Prefer latest big (pro) and small (flash)
        prefer_pro = ["gemini-2.5-pro-latest", "gemini-2.5-pro", "gemini-2-pro", "gemini-2-latest"]
        prefer_flash = ["gemini-2.5-flash-latest", "gemini-2.5-flash", "gemini-2-flash", "gemini-2-latest"]
        picks: list[str] = []
        for p in prefer_pro:
            if p in avail:
                picks.append(p); break
        for p in prefer_flash:
            if p in avail:
                if not picks or picks[-1] != p:
                    picks.append(p)
                break
        if not picks:
            picks = [getattr(config, "GOOGLE_MODEL", "gemini-2.5-flash"), "gemini-2.5-pro"]
        ids = picks
    except Exception:
        # Fallback to curated list emphasizing latest/pro
        ids = [getattr(config, "GOOGLE_MODEL", "gemini-2.5-flash"), "gemini-2.5-pro"]
    # Dedup + prefer -latest, then numeric desc, then pro before flash
    def sort_key(x: str):
        xl = x.lower()
        latest = xl.endswith('-latest')
        pro = '-pro' in xl
        # crude numeric extraction for 2.5, 2.0, 3.0 etc.
        import re
        m = re.search(r'gemini-(\d+(?:\.\d+)?)', xl)
        ver = float(m.group(1)) if m else 0.0
        return (0 if latest else 1, -ver, 0 if pro else 1, xl)
    # Keep at most 2 (pro + flash)
    seen: set[str] = set(); out = []
    for it in sorted(ids, key=sort_key):
        if it not in seen:
            seen.add(it); out.append(it)
        if len(out) >= 2:
            break
    return _cache_set("gemini", out)

@app.get("/api/models")
async def list_models(provider: str = "auto", q: str = ""):
    prov = (provider or "auto").lower()
    query = (q or "").strip().lower()
    models: list[str]
    if prov == 'gemini':
        models = _list_gemini_latest()
    elif prov == 'openai':
        models = _list_openai_latest()
    else:
        # Merge top picks only (1 per provider)
        g = _list_gemini_latest()
        o = _list_openai_latest()
        models = g + o
    if query:
        models = [m for m in models if query in m.lower()]
    return {"models": models}

@app.post("/api/notes/text")
async def create_text_note(request: Request):
    """Create a note directly from provided transcription text (no audio).

    Body JSON: { transcription: string, title?: string, date?: string, folder?: string, tags?: [{label,color?}] }
    Returns: { filename }
    """
    try:
        body = await request.json()
        transcription = str((body or {}).get("transcription") or "").strip()
        title = str((body or {}).get("title") or "").strip()
        date_override = str((body or {}).get("date") or "").strip()
        folder = str((body or {}).get("folder") or "").strip()
        tags = (body or {}).get("tags") or []
        if not transcription:
            return Response(status_code=400)

        # Generate a unique id and pseudo filename (non-audio)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        nid = f"text-{stamp}-{uuid.uuid4().hex[:6]}"
        pseudo_filename = f"{nid}.txt"

        # Auto-generate title if missing via Gemini with OpenAI fallback
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
                    # Fallback: derive from transcription snippet instead of id
                    words = (transcription or '').strip().split()
                    title = ' '.join(words[:8]) if words else 'Text Note'

        # Build payload similar to build_note_payload but without audio metadata
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
            "tags": [ {"label": str((t or {}).get("label") or "").strip(), "color": (t or {}).get("color") } for t in tags if isinstance(t, dict) and (t.get("label") or "").strip() ],
        }
        # Persist JSON
        os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
        with open(os.path.join(TRANSCRIPTS_DIR, f"{nid}.json"), 'w') as jf:
            json.dump(data, jf, ensure_ascii=False)
        return {"filename": pseudo_filename}
    except Exception as e:
        return {"error": str(e)}

@app.patch("/api/notes/{filename}/tags")
async def update_tags(filename: str, payload: TagsUpdate):
    """Update user-defined tags for a note (stored in JSON)."""
    base_filename = os.path.splitext(filename)[0]
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
    # Ensure a JSON exists
    if not os.path.exists(json_path):
        return Response(status_code=404)
    try:
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        # Normalize tags into list of {label, color}
        tags = []
        for t in payload.tags:
            tags.append({"label": t.label, "color": t.color})
        data["tags"] = tags
        with open(json_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        return {"status": "ok", "tags": tags}
    except Exception as e:
        return {"error": str(e)}

@app.patch("/api/notes/{filename}/folder")
async def update_folder(filename: str, payload: FolderUpdate):
    """Update the folder for a note (stored in JSON). Pass folder: string or null/empty to clear."""
    base_filename = os.path.splitext(filename)[0]
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
    if not os.path.exists(json_path):
        # Create a minimal JSON so folder assignment works even before transcription
        try:
            audio_path = os.path.join(VOICE_NOTES_DIR, filename)
            if not os.path.exists(audio_path):
                # try to find by any known extension
                for ext in ('.wav', '.ogg', '.webm', '.m4a', '.mp3'):
                    p = os.path.join(VOICE_NOTES_DIR, base_filename + ext)
                    if os.path.exists(p):
                        audio_path = p
                        filename = os.path.basename(p)
                        break
            import note_store as _ns
            # Use base as title, empty transcription (will be filled when background task runs)
            audio_ext = os.path.splitext(filename)[1].lstrip('.').lower() or 'wav'
            stored_mime = {
                'm4a': 'audio/mp4',
                'mp3': 'audio/mpeg',
                'wav': 'audio/wav',
                'ogg': 'audio/ogg',
                'webm': 'audio/webm',
            }.get(audio_ext, f"audio/{audio_ext}" if audio_ext else 'audio/wav')
            metadata_fields = {
                "audio_format": audio_ext,
                "stored_mime": stored_mime,
                "original_format": audio_ext,
                "transcoded": False,
            }
            if audio_ext == 'm4a':
                metadata_fields["sample_rate_hz"] = 44100
            elif audio_ext == 'wav':
                metadata_fields["sample_rate_hz"] = 16000
            payload_min = _ns.build_note_payload(filename, base_filename, "", metadata_fields)
            _ns.save_note_json(base_filename, payload_min)
        except Exception:
            return Response(status_code=404)
    try:
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        data["folder"] = (payload.folder or "").strip()
        with open(json_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        return {"status": "ok", "folder": data["folder"]}
    except Exception as e:
        return {"error": str(e)}

# ----------------- Narratives API -----------------

@app.get("/api/narratives")
async def list_narratives():
    if not os.path.exists(NARRATIVES_DIR):
        os.makedirs(NARRATIVES_DIR)
    files = [f for f in sorted(os.listdir(NARRATIVES_DIR)) if f.endswith('.txt')]
    return files

@app.get("/api/narratives/{filename}")
async def get_narrative(filename: str):
    path = os.path.join(NARRATIVES_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
        # Try to include a generated/display title if available
        title = None
        try:
            mp = os.path.join(NARRATIVE_META_DIR, f"{filename}.json")
            if os.path.exists(mp):
                with open(mp, 'r') as mf:
                    md = json.load(mf)
                title = (md or {}).get('title')
        except Exception:
            title = None
        return {"content": content, "title": title}
    return Response(status_code=404)

@app.delete("/api/narratives/{filename}")
async def delete_narrative(filename: str):
    path = os.path.join(NARRATIVES_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return Response(status_code=200)
    return Response(status_code=404)

@app.post("/api/narratives")
async def create_narrative_from_notes(request: Request):
    """Create a simple narrative by concatenating selected notes' titles and transcriptions.

    Expects JSON body: [{"filename": "...wav"}, ...]
    Writes a .txt file into narratives/ and returns its filename.
    """
    try:
        items = await request.json()
        if not isinstance(items, list):
            return Response(status_code=400)
        parts = []
        for it in items:
            name = (it or {}).get('filename')
            if not name or not isinstance(name, str):
                continue
            base = os.path.splitext(name)[0]
            json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
            title = base
            text = ''
            if os.path.exists(json_path):
                import json
                with open(json_path, 'r') as jf:
                    data = json.load(jf)
                title = data.get('title') or title
                text = data.get('transcription') or ''
            parts.append(f"# {title}\n\n{text}\n\n")
        if not parts:
            return Response(status_code=400)
        if not os.path.exists(NARRATIVES_DIR):
            os.makedirs(NARRATIVES_DIR)
        from datetime import datetime
        name = f"narrative-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        out = os.path.join(NARRATIVES_DIR, name)
        content = "\n".join(parts)
        with open(out, 'w') as f:
            f.write(content)
        # Generate a short title for this narrative and save metadata
        try:
            os.makedirs(NARRATIVE_META_DIR, exist_ok=True)
            # Prefer first heading or first non-empty line as quick baseline
            title = None
            for ln in content.splitlines():
                s = (ln or '').strip()
                if not s: continue
                if s.startswith('#'):
                    s = s.lstrip('#').strip()
                title = s
                break
            # Refine via LLM if possible
            if title:
                try:
                    msg = HumanMessage(content=[{"type": "text", "text": (
                        "Return exactly one short title (5–8 words) for the narrative below. "
                        "Do not include quotes, bullets, markdown, or extra text. Output only the title on one line.\n\n" + content[:4000]
                    )}])
                    resp, _ = await asyncio.to_thread(providers.invoke_google, [msg])
                    title_llm = providers.normalize_title_output(getattr(resp, 'content', ''))
                    if title_llm:
                        title = title_llm
                except Exception:
                    try:
                        from langchain_core.messages import HumanMessage as _HM
                        title = providers.title_with_openai(content[:4000]) or title
                    except Exception:
                        pass
            if not title:
                title = os.path.splitext(name)[0]
            with open(os.path.join(NARRATIVE_META_DIR, f"{name}.json"), 'w') as mf:
                json.dump({"title": title}, mf, ensure_ascii=False)
        except Exception:
            pass
        return {"filename": name}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/narratives/generate")
async def generate_narrative(request: Request):
    """Generate a narrative from selected notes and optional extra context via Gemini/OpenAI.

    Body JSON:
    {
      "items": [{"filename": "...wav"}, ...],
      "extra_text": "optional",
      "provider": "auto" | "gemini" | "openai",
      "model": "optional override",
      "temperature": 0.2,
      "system": "optional system instruction"
    }
    Returns: {"filename": "narrative-...txt"}
    """
    try:
        body = await request.json()
        items = (body or {}).get("items", [])
        extra_text = (body or {}).get("extra_text", "")
        provider_choice = ((body or {}).get("provider") or "auto").lower()
        model_override = (body or {}).get("model")
        temperature = float((body or {}).get("temperature") or 0.2)
        system_inst = (body or {}).get("system") or (
            "You are an expert editor. Synthesize a cohesive, structured narrative from the provided notes and context. "
            "Focus on clarity, key insights, and concrete action items. Keep it concise and readable."
        )
        parent_filename = (body or {}).get("parent") or None
        # Optional saved format task prompt (id or inline prompt)
        format_id = (body or {}).get("format_id")
        format_ids = (body or {}).get("format_ids") or []
        format_prompt_inline = (body or {}).get("format_prompt")

        # Collect sources (notes or existing narratives) with diagnostics
        if not isinstance(items, list):
            return Response(status_code=400)
        sources = []
        dbg_sources = []  # diagnostics for user: title/date/length/preview per source
        for it in items:
            name = (it or {}).get("filename")
            if not name or not isinstance(name, str):
                continue
            base = os.path.splitext(name)[0]
            title = base
            text = ""
            date_str = ""
            kind = "note"
            if name.lower().endswith('.txt'):
                # If it's a real narrative file, use its content; otherwise, treat as note JSON-only
                narr_path = os.path.join(NARRATIVES_DIR, name)
                if os.path.exists(narr_path):
                    try:
                        with open(narr_path, 'r') as nf:
                            text = nf.read()
                    except Exception:
                        text = ""
                    # try meta title/date
                    try:
                        mp = os.path.join(NARRATIVE_META_DIR, f"{name}.json")
                        if os.path.exists(mp):
                            with open(mp, 'r') as mf:
                                md = json.load(mf)
                            title = md.get('title') or title
                            date_str = (md.get('date') or '').strip()
                    except Exception:
                        pass
                    kind = "narrative"
                else:
                    # Fall back to note JSON by base name
                    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
                    if os.path.exists(json_path):
                        import json
                        with open(json_path, "r") as jf:
                            data = json.load(jf)
                        title = data.get("title") or title
                        text = data.get("transcription") or ""
                        date_str = (data.get("date") or "").strip()
                    kind = "note"
            else:
                # Note JSON source
                json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
                if os.path.exists(json_path):
                    import json
                    with open(json_path, "r") as jf:
                        data = json.load(jf)
                    title = data.get("title") or title
                    text = data.get("transcription") or ""
                    date_str = (data.get("date") or "").strip()
                # If date missing, derive from audio mtime or filename pattern
                if not date_str:
                    try:
                        ap = None
                        try:
                            ap = _ns._find_audio_path(base, data if 'data' in locals() else {})
                        except Exception:
                            ap = None
                        if ap and os.path.exists(ap):
                            mtime = os.path.getmtime(ap)
                            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                        else:
                            # Try parsing YYYYMMDD from base
                            import re
                            m = re.match(r"^(\\d{4})(\\d{2})(\\d{2})", base)
                            if m:
                                date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                    except Exception:
                        pass
            # Normalize low-quality titles like id-looking placeholders
            try:
                if (not title) or title.lower() in ("untitled", "title generation failed."):
                    title = (text or '').strip().split('\n', 1)[0].strip() or (title or '')
                import re as _re
                if _re.fullmatch(r"text-\d{14,}-[a-f0-9]{4,}", title or ''):
                    # derive from first words of content
                    head = ' '.join(((text or '').strip().split() or [])[:8]).strip()
                    title = head or 'Text Note'
            except Exception:
                pass
            # Build diagnostics for this source
            try:
                preview = (text or '').strip().replace("\n", " ")[:140]
                dbg_sources.append({
                    "kind": kind,
                    "filename": name,
                    "title": (title or '')[:120],
                    "date": date_str or "",
                    "text_len": len(text or ''),
                    "text_preview": preview,
                })
            except Exception:
                pass
            # Skip entirely empty entries
            if not (text or '').strip():
                continue
            sources.append({"title": title, "text": text, "date": date_str or ""})

        if not sources and not extra_text.strip():
            return Response(status_code=400)

        # Build prompt
        parts = [system_inst.strip()]
        # If a saved format or inline format prompt present, add it at top as task instruction
        try:
            fmt_chunks = []
            # single id
            if format_id:
                p = os.path.join(FORMATS_DIR, f"{format_id}.json")
                if os.path.exists(p):
                    with open(p, 'r') as f:
                        fmt = json.load(f)
                    t = (fmt or {}).get('prompt')
                    if t: fmt_chunks.append(str(t))
            # multiple ids
            if isinstance(format_ids, list):
                for fid in format_ids:
                    try:
                        p = os.path.join(FORMATS_DIR, f"{fid}.json")
                        if os.path.exists(p):
                            with open(p, 'r') as f:
                                fmt = json.load(f)
                            t = (fmt or {}).get('prompt')
                            if t: fmt_chunks.append(str(t))
                    except Exception:
                        continue
            # inline prompt
            if format_prompt_inline:
                fmt_chunks.append(str(format_prompt_inline))
            if fmt_chunks:
                parts.append("\n\nTask Formats:\n" + "\n\n---\n\n".join([c.strip() for c in fmt_chunks if c and c.strip()]))
        except Exception:
            pass
        parts.append("\n\nContext Notes:\n")
        for i, src in enumerate(sources, start=1):
            t = src.get("title")
            tx = src.get("text") or ""
            d = (src.get("date") or "").strip()
            header = f"[{i}] {d} — {t}" if d else f"[{i}] {t}"
            parts.append(f"{header}\n{tx}\n")
        if extra_text.strip():
            parts.append("\nAdditional Context:\n" + extra_text.strip() + "\n")
        parts.append("\nWrite the narrative now.")
        prompt_text = "\n".join(parts)
        try:
            logging.info("[gen] items=%s sources=%s", len(items), json.dumps(dbg_sources)[:2000])
            logging.info("[gen] prompt_head=%s", (prompt_text[:800] + ('…' if len(prompt_text)>800 else '')))
        except Exception:
            pass

        # Call provider
        content = None
        key_index = None
        provider_used = provider_choice
        model_used = model_override or (config.GOOGLE_MODEL if provider_choice != "openai" else config.OPENAI_NARRATIVE_MODEL)
        if provider_choice in ("auto", "gemini"):
            try:
                resp, key_index = await asyncio.to_thread(
                    providers.invoke_google,
                    [HumanMessage(content=[{"type": "text", "text": prompt_text}])],
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

        # Generate and persist a short display title for this narrative
        try:
            os.makedirs(NARRATIVE_META_DIR, exist_ok=True)
            title = None
            # Prefer first heading or first non-empty line if model fails
            for ln in (content or '').splitlines():
                s = (ln or '').strip()
                if not s: continue
                if s.startswith('#'):
                    s = s.lstrip('#').strip()
                title = s
                break
            try:
                msg = HumanMessage(content=[{"type": "text", "text": (
                    "Return exactly one short title (5–8 words) for the narrative below. "
                    "Do not include quotes, bullets, markdown, or extra text. Output only the title on one line.\n\n" + (content or '')[:4000]
                )}])
                resp, _ = await asyncio.to_thread(providers.invoke_google, [msg])
                title_llm = providers.normalize_title_output(getattr(resp, 'content', ''))
                if title_llm:
                    title = title_llm
            except Exception:
                try:
                    title_oa = providers.title_with_openai((content or '')[:4000])
                    if title_oa:
                        title = title_oa
                except Exception:
                    pass
            if not title:
                title = os.path.splitext(name)[0]
            with open(os.path.join(NARRATIVE_META_DIR, f"{name}.json"), 'w') as mf:
                json.dump({"title": title}, mf, ensure_ascii=False)
        except Exception:
            pass

        # --- Version threading: record parent→child relationship ---
        try:
            def _threads_path():
                return os.path.join(NARRATIVES_DIR, "threads.json")

            def _load_threads():
                p = _threads_path()
                if not os.path.exists(p):
                    return {"threads": [], "map": {}}
                with open(p, "r") as tf:
                    return json.load(tf)

            def _save_threads(data):
                p = _threads_path()
                tmp = p + ".tmp"
                with open(tmp, "w") as tf:
                    json.dump(data, tf)
                os.replace(tmp, p)

            if parent_filename:
                data = _load_threads()
                mp = data.get("map", {})
                threads = data.get("threads", [])
                thread_id = mp.get(parent_filename)
                if not thread_id:
                    # Create a new thread starting from parent
                    base = os.path.splitext(parent_filename)[0]
                    thread_id = base
                    # Ensure uniqueness
                    existing_ids = {t.get("id") for t in threads}
                    idx = 1
                    while thread_id in existing_ids:
                        idx += 1
                        thread_id = f"{base}-{idx}"
                    threads.append({
                        "id": thread_id,
                        "files": [parent_filename, name],
                    })
                    mp[parent_filename] = thread_id
                    mp[name] = thread_id
                else:
                    # Append to existing thread if not already present
                    for t in threads:
                        if t.get("id") == thread_id:
                            if name not in t.get("files", []):
                                t.setdefault("files", []).append(name)
                            break
                    mp[name] = thread_id
                data["map"] = mp
                data["threads"] = threads
                _save_threads(data)
        except Exception:
            pass

        try:
            usage.log_usage(
                event="narrative",
                provider=provider_used,
                model=model_used,
                key_label=(providers.key_label_from_index(key_index or 0) if provider_used == "gemini" else usage.OPENAI_LABEL),
                status="success",
            )
        except Exception:
            pass

        return {"filename": name}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/narratives/thread/{filename}")
async def get_thread(filename: str):
    """Return the version thread (files and index) for a given narrative file."""
    try:
        path = os.path.join(NARRATIVES_DIR, "threads.json")
        if not os.path.exists(path):
            return {"files": [filename], "index": 0}
        with open(path, "r") as f:
            data = json.load(f)
        mp = data.get("map", {})
        th_id = mp.get(filename)
        if not th_id:
            return {"files": [filename], "index": 0}
        for t in data.get("threads", []):
            if t.get("id") == th_id:
                files = t.get("files", [])
                try:
                    idx = files.index(filename)
                except ValueError:
                    idx = 0
                return {"files": files, "index": idx}
        return {"files": [filename], "index": 0}
    except Exception as e:
        return {"error": str(e)}


# ----------------- Formats API -----------------

@app.get("/api/formats")
async def list_formats():
    os.makedirs(FORMATS_DIR, exist_ok=True)
    out = []
    for fn in sorted(os.listdir(FORMATS_DIR)):
        if fn.endswith('.json'):
            try:
                with open(os.path.join(FORMATS_DIR, fn), 'r') as f:
                    data = json.load(f)
                # Ensure id from filename if missing
                fid = data.get('id') or os.path.splitext(fn)[0]
                out.append({
                    'id': fid,
                    'title': data.get('title') or fid,
                    'prompt': data.get('prompt') or ''
                })
            except Exception:
                continue
    return out


@app.post("/api/formats")
async def create_or_update_format(request: Request):
    try:
        body = await request.json()
        title = (body or {}).get('title')
        prompt = (body or {}).get('prompt')
        fid = (body or {}).get('id')
        if not title or not prompt:
            return Response(status_code=400)
        os.makedirs(FORMATS_DIR, exist_ok=True)
        if not fid:
            import uuid as _uuid
            fid = _uuid.uuid4().hex[:12]
        path = os.path.join(FORMATS_DIR, f"{fid}.json")
        with open(path, 'w') as f:
            json.dump({'id': fid, 'title': title, 'prompt': prompt}, f, ensure_ascii=False)
        return {'id': fid}
    except Exception as e:
        return {"error": str(e)}


# ----------------- Narrative Folders API -----------------

def _narrative_meta_path(filename: str) -> str:
    os.makedirs(NARRATIVE_META_DIR, exist_ok=True)
    return os.path.join(NARRATIVE_META_DIR, f"{filename}.json")

def _read_narrative_meta(filename: str) -> dict:
    try:
        p = _narrative_meta_path(filename)
        if os.path.exists(p):
            with open(p, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _write_narrative_meta(filename: str, data: dict) -> None:
    os.makedirs(NARRATIVE_META_DIR, exist_ok=True)
    p = _narrative_meta_path(filename)
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data or {}, f, ensure_ascii=False)
    os.replace(tmp, p)

@app.get("/api/narratives/list")
async def list_narratives_meta():
    os.makedirs(NARRATIVES_DIR, exist_ok=True)
    files = [f for f in sorted(os.listdir(NARRATIVES_DIR)) if f.endswith('.txt')]
    out = []
    for fn in files:
        meta = _read_narrative_meta(fn)
        out.append({
            'filename': fn,
            'title': meta.get('title'),
            'folder': (meta.get('folder') or '').strip(),
        })
    return out

@app.patch("/api/narratives/{filename}/folder")
async def set_narrative_folder(filename: str, request: Request):
    try:
        body = await request.json()
        folder = str((body or {}).get('folder') or '').strip()
        meta = _read_narrative_meta(filename)
        meta['folder'] = folder
        _write_narrative_meta(filename, meta)
        return { 'status': 'ok', 'folder': folder }
    except Exception as e:
        return { 'error': str(e) }

@app.get("/api/narratives/folders")
async def list_narrative_folders():
    os.makedirs(NARRATIVES_DIR, exist_ok=True)
    files = [f for f in sorted(os.listdir(NARRATIVES_DIR)) if f.endswith('.txt')]
    counts: dict[str,int] = {}
    for fn in files:
        try:
            meta = _read_narrative_meta(fn)
            folder = (meta.get('folder') or '').strip()
            if folder:
                counts[folder] = counts.get(folder, 0) + 1
        except Exception:
            continue
    out = [{ 'name': k, 'count': v } for k,v in sorted(counts.items(), key=lambda kv: kv[0].lower())]
    return out


# ----------------- Folders API -----------------

def _folders_registry_path() -> str:
    os.makedirs(config.FOLDERS_DIR, exist_ok=True)
    return os.path.join(config.FOLDERS_DIR, "folders.json")

def _load_folders_registry() -> list[str]:
    try:
        p = _folders_registry_path()
        if not os.path.exists(p):
            return []
        with open(p, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str)]
        return []
    except Exception:
        return []

def _save_folders_registry(names: list[str]) -> None:
    p = _folders_registry_path()
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(sorted(list({n.strip(): None for n in names if n and isinstance(n, str)}.keys()), key=lambda s: s.lower()), f, ensure_ascii=False)
    os.replace(tmp, p)


@app.get("/api/folders")
async def list_folders():
    """Return a list of folders with counts, combining registry + derived from note JSONs."""
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    counts: dict[str, int] = {}
    for fn in os.listdir(TRANSCRIPTS_DIR):
        if not fn.endswith('.json'):
            continue
        try:
            with open(os.path.join(TRANSCRIPTS_DIR, fn), 'r') as f:
                data = json.load(f)
            folder = (data.get('folder') or '').strip()
            if folder:
                counts[folder] = counts.get(folder, 0) + 1
        except Exception:
            continue
    # include zero-count folders from registry
    reg = _load_folders_registry()
    for n in reg:
        counts.setdefault(n, 0)
    out = [{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: kv[0].lower())]
    return out

@app.post("/api/folders")
async def create_folder(request: Request):
    try:
        body = await request.json()
        name = str((body or {}).get("name") or "").strip()
        if not name:
            return Response(status_code=400)
        # basic sanitation: disallow path separators
        if "/" in name or "\\" in name:
            return Response(status_code=400)
        reg = _load_folders_registry()
        if name not in reg:
            reg.append(name)
            _save_folders_registry(reg)
        return {"name": name}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/api/folders/{name}")
async def delete_folder(name: str):
    """Delete a folder and PERMANENTLY DELETE all notes inside it.

    Removes the folder from the registry and deletes corresponding audio files
    and transcription JSONs for notes assigned to that folder.
    """
    try:
        clean = (name or "").strip()
        reg = _load_folders_registry()
        # Delete notes in this folder
        deleted_notes = 0
        import note_store as _ns
        for fn in list(os.listdir(TRANSCRIPTS_DIR)):
            if not fn.endswith('.json'):
                continue
            jp = os.path.join(TRANSCRIPTS_DIR, fn)
            try:
                with open(jp, 'r') as f:
                    data = json.load(f)
                if (data.get('folder') or '').strip() == clean:
                    base = os.path.splitext(fn)[0]
                    # locate audio
                    ap = None
                    try:
                        ap = _ns._find_audio_path(base, data)
                    except Exception:
                        ap = None
                    # delete files
                    if ap and os.path.exists(ap):
                        try: os.remove(ap)
                        except Exception: pass
                    try: os.remove(jp)
                    except Exception: pass
                    deleted_notes += 1
            except Exception:
                continue
        # Remove folder from registry
        if clean in reg:
            reg = [n for n in reg if n != clean]
            _save_folders_registry(reg)
        return {"deleted": clean, "notes_deleted": deleted_notes}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/formats/{fid}")
async def delete_format(fid: str):
    try:
        path = os.path.join(FORMATS_DIR, f"{fid}.json")
        if os.path.exists(path):
            os.remove(path)
            return Response(status_code=200)
        return Response(status_code=404)
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
