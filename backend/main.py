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
from utils import on_startup
import uvicorn
import os
from datetime import datetime

app = FastAPI()

# Configure CORS to allow requests from the SvelteKit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # The default SvelteKit dev server address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for voice notes
VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_notes'))
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.wav"
    file_path = os.path.join(VOICE_NOTES_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    
    # Start transcription and title generation in the background
    print(f"File saved: {filename}. Adding transcription to background tasks.")
    background_tasks.add_task(transcribe_and_save, file_path)
    
    return {"filename": filename, "message": "File upload successful, transcription started."}

@app.delete("/api/notes/{filename}")
async def delete_note(filename: str):
    """API endpoint to delete a note."""
    file_path = os.path.join(VOICE_NOTES_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        
        # Delete associated files
        base_filename = filename.replace('.wav', '')
        txt_path = os.path.join(VOICE_NOTES_DIR, f"{base_filename}.txt")
        title_path = os.path.join(VOICE_NOTES_DIR, f"{base_filename}.title")
        if os.path.exists(txt_path):
            os.remove(txt_path)
        if os.path.exists(title_path):
            os.remove(title_path)
            
        return Response(status_code=200)
    return Response(status_code=404)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
