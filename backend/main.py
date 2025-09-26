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
from services import process_interaction, get_notes, transcribe_and_save
from models import TagsUpdate
from utils import on_startup
import uvicorn
import os
from datetime import datetime
import uuid

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

# Mount static files directory for voice notes
VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_notes'))
TRANSCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'transcriptions'))
NARRATIVES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'narratives'))
app.mount("/voice_notes", StaticFiles(directory=VOICE_NOTES_DIR), name="voice_notes")

@app.on_event("startup")
async def startup_event():
    await on_startup()

@app.post("/narrative/interaction")
async def handle_interaction(
    audio_file: UploadFile = File(...), 
    current_scenario_id: str = Form(...)
):
    """
    This endpoint receives audio and the current scenario ID,
    processes them, and returns the next scenario.
    """
    result = process_interaction(audio_file.file, current_scenario_id)
    return result

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
            wav = (it or {}).get('filename')
            if not wav or not wav.endswith('.wav'):
                continue
            base = wav[:-4]
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
