import os
import shutil
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import dotenv

from models import Note
from services import transcribe_and_save
from utils import on_startup

# Load environment variables from .env file
dotenv.load_dotenv()

# --- FastAPI App Setup ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_NOTES_DIR = os.path.join(APP_DIR, "voice_notes")
app = FastAPI()

# --- Middleware ---
app.mount("/voice_notes", StaticFiles(directory=VOICE_NOTES_DIR), name="voice_notes")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    await on_startup()

@app.get("/api/notes", response_model=List[Note])
def get_notes():
    """Returns a list of notes with their transcriptions."""
    notes = []
    wav_files = sorted(
        [f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.wav')],
        key=lambda f: os.path.getmtime(os.path.join(VOICE_NOTES_DIR, f)),
        reverse=True
    )

    for wav_file in wav_files:
        transcription_path = os.path.join(VOICE_NOTES_DIR, wav_file.replace('.wav', '.txt'))
        title_path = os.path.join(VOICE_NOTES_DIR, wav_file.replace('.wav', '.title'))
        
        transcription = "Transcription in progress..."
        if os.path.exists(transcription_path):
            with open(transcription_path, 'r') as f:
                transcription = f.read()
        
        title = "Title generation in progress..."
        if os.path.exists(title_path):
            with open(title_path, 'r') as f:
                title = f.read()

        notes.append(Note(filename=wav_file, transcription=transcription, title=title))
    return notes

@app.post("/api/notes")
async def create_note(file: UploadFile = File(...), date: Optional[str] = None, place: Optional[str] = None):
    """Receives an audio file, saves it, and triggers transcription."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename_parts = [timestamp]
    if date:
        filename_parts.append(date.replace(" ", "_").replace("/", "_"))
    if place:
        filename_parts.append(place.replace(" ", "_").replace("/", "_"))

    filename_base = "_".join(filename_parts)
    filename_wav = f"note_{filename_base}.wav"
    
    wav_path = os.path.join(VOICE_NOTES_DIR, filename_wav)

    # Save the uploaded audio file
    try:
        with open(wav_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Transcribe the audio and save it
    try:
        await transcribe_and_save(wav_path)
    except Exception as e:
        if "429" in str(e):
            raise HTTPException(status_code=429, detail="You have exceeded your Google API quota. Please upgrade your plan.")
        else:
            raise HTTPException(status_code=500, detail=f"An error occurred during transcription: {e}")

    return {"filename": filename_wav}

@app.delete("/api/notes/{filename}")
def delete_note(filename: str):
    """Deletes a note and its associated files."""
    wav_path = os.path.join(VOICE_NOTES_DIR, filename)
    txt_path = os.path.join(VOICE_NOTES_DIR, filename.replace('.wav', '.txt'))
    title_path = os.path.join(VOICE_NOTES_DIR, filename.replace('.wav', '.title'))

    deleted = False
    for path in [wav_path, txt_path, title_path]:
        if os.path.exists(path):
            os.remove(path)
            deleted = True

    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")

    return {"message": "Note deleted successfully"}

@app.get("/api/narratives")
def get_narratives():
    """Returns a list of narrative files."""
    narratives_dir = os.path.join(APP_DIR, "narratives")
    if not os.path.exists(narratives_dir):
        return []
    return sorted(
        [f for f in os.listdir(narratives_dir) if f.endswith('.txt')],
        key=lambda f: os.path.getmtime(os.path.join(narratives_dir, f)),
        reverse=True
    )

@app.get("/api/narratives/{filename}")
def get_narrative_content(filename: str):
    """Returns the content of a narrative file."""
    narrative_path = os.path.join(APP_DIR, "narratives", filename)
    if not os.path.exists(narrative_path):
        raise HTTPException(status_code=404, detail="Narrative not found")
    with open(narrative_path, 'r') as f:
        return {"content": f.read()}

@app.delete("/api/narratives/{filename}")
def delete_narrative(filename: str):
    """Deletes a narrative file."""
    narrative_path = os.path.join(APP_DIR, "narratives", filename)
    if not os.path.exists(narrative_path):
        raise HTTPException(status_code=404, detail="Narrative not found")
    os.remove(narrative_path)
    return {"message": "Narrative deleted successfully"}