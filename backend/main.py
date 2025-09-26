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
from models import TagsUpdate
from utils import on_startup
import uvicorn
import os
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

# Mount static files directory for voice notes
app.mount("/voice_notes", StaticFiles(directory=VOICE_NOTES_DIR), name="voice_notes")

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
        parts = [system_inst.strip(), "\n\nContext Notes:\n"]
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
