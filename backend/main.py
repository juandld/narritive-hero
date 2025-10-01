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
from langchain_core.messages import HumanMessage
import providers
import config

app = FastAPI()

# Configure CORS to allow requests from the SvelteKit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use centralized config paths, but keep module vars for tests to monkeypatch
VOICE_NOTES_DIR = config.VOICE_NOTES_DIR
TRANSCRIPTS_DIR = config.TRANSCRIPTS_DIR
NARRATIVES_DIR = config.NARRATIVES_DIR
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
    place: str = Form(None)
):
    """API endpoint to upload a new note."""
    ct = (file.content_type or '').lower()
    if 'webm' in ct:
        ext = 'webm'
    elif 'ogg' in ct:
        ext = 'ogg'
    elif 'm4a' in ct:
        ext = 'm4a'
    elif 'mp3' in ct:
        ext = 'mp3'
    else:
        ext = 'wav'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{uuid.uuid4().hex[:6]}.{ext}"
    file_path = os.path.join(VOICE_NOTES_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    
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
    if os.path.exists(file_path):
        os.remove(file_path)
        # Delete associated JSON (and legacy txt)
        base_filename = os.path.splitext(filename)[0]
        json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
        legacy_txt_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.txt")
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(legacy_txt_path):
            os.remove(legacy_txt_path)
        return Response(status_code=200)
    return Response(status_code=404)

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
            payload_min = _ns.build_note_payload(filename, base_filename, "")
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
        return {"content": content}
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
        with open(out, 'w') as f:
            f.write("\n".join(parts))
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

        # Collect sources
        if not isinstance(items, list):
            return Response(status_code=400)
        sources = []
        for it in items:
            name = (it or {}).get("filename")
            if not name or not isinstance(name, str):
                continue
            base = os.path.splitext(name)[0]
            json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
            title = base
            text = ""
            if os.path.exists(json_path):
                import json
                with open(json_path, "r") as jf:
                    data = json.load(jf)
                title = data.get("title") or title
                text = data.get("transcription") or ""
            sources.append((title, text))

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
        for i, (title, text) in enumerate(sources, start=1):
            parts.append(f"[{i}] {title}\n{text}\n")
        if extra_text.strip():
            parts.append("\nAdditional Context:\n" + extra_text.strip() + "\n")
        parts.append("\nWrite the narrative now.")
        prompt_text = "\n".join(parts)

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
    """Delete a folder and clear it from any notes using it."""
    try:
        clean = (name or "").strip()
        reg = _load_folders_registry()
        if clean in reg:
            reg = [n for n in reg if n != clean]
            _save_folders_registry(reg)
        # Clear from notes
        cleared = 0
        for fn in os.listdir(TRANSCRIPTS_DIR):
            if not fn.endswith('.json'):
                continue
            jp = os.path.join(TRANSCRIPTS_DIR, fn)
            try:
                with open(jp, 'r') as f:
                    data = json.load(f)
                if (data.get('folder') or '').strip() == clean:
                    data['folder'] = ""
                    with open(jp, 'w') as f:
                        json.dump(data, f, ensure_ascii=False)
                    cleared += 1
            except Exception:
                continue
        return {"deleted": clean, "cleared": cleared}
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
