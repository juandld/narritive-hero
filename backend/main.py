import os
import shutil
import base64
import asyncio
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
from pydantic import BaseModel
import dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# Load environment variables from .env file
dotenv.load_dotenv()

# --- Pydantic Models ---
from typing import List, Optional

class Note(BaseModel):
    filename: str
    transcription: Optional[str] = None
    title: Optional[str] = None

# --- FastAPI App Setup ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_NOTES_DIR = os.path.join(APP_DIR, "voice_notes")
app = FastAPI()

# --- Transcription Model ---
# Make sure your GOOGLE_API_KEY is set in the .env file
# Using a model that supports audio input
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

# --- Middleware ---
app.mount(f"/{VOICE_NOTES_DIR}", StaticFiles(directory=VOICE_NOTES_DIR), name=VOICE_NOTES_DIR)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- Helper Functions ---
async def generate_title(prompt: str, llm_instance) -> str:
    """Generates a concise title from the given prompt."""
    print("Generating title...")
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": prompt,
            }
        ]
    )
    response = await llm_instance.ainvoke([message])
    title = response.content.strip()
    print(f"Generated title: {title}")
    return title

async def transcribe_and_save(wav_path: str):
    """Transcribes a single audio file and saves the transcription."""
    txt_path = wav_path.replace('.wav', '.txt')
    print(f"Transcribing {os.path.basename(wav_path)}...")

    with open(wav_path, "rb") as audio_file:
        audio_bytes = audio_file.read()

    encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')

    transcription_prompt = "Transcribe this audio recording accurately."

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": transcription_prompt,
            },
            {
                "type": "media",
                "mime_type": "audio/wav",
                "data": encoded_audio,
            },
        ]
    )

    response = await llm.ainvoke([message])
    transcription = response.content

    with open(txt_path, 'w') as f:
        f.write(transcription)
    print(f"Finished transcribing {os.path.basename(wav_path)}.")

    # Generate and save title
    try:
        title_prompt = f"Generate a concise title (under 10 words) for the following audio transcription:\n\n{transcription}"

        title = await generate_title(title_prompt, llm)
        title_path = wav_path.replace('.wav', '.title')
        with open(title_path, 'w') as f:
            f.write(title)
    except Exception as e:
        print(f"Error generating title for {os.path.basename(wav_path)}: {e}")
        title_path = wav_path.replace('.wav', '.title')
        with open(title_path, 'w') as f:
            f.write("Title generation failed.")



# --- API Endpoints ---
@app.on_event("startup")
async def on_startup():
    """On startup, create voice notes dir and backfill any missing transcriptions."""
    if not os.path.exists(VOICE_NOTES_DIR):
        os.makedirs(VOICE_NOTES_DIR)
    
    print("Checking for missing transcriptions...")
    wav_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.wav')}
    txt_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.txt')}
    title_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.title')}

    tasks = []
    for wav_file in wav_files:
        txt_filename = wav_file.replace('.wav', '.txt')
        title_filename = wav_file.replace('.wav', '.title')
        if txt_filename not in txt_files or title_filename not in title_files:
            wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
            tasks.append(transcribe_and_save(wav_path))
        else:
            # Check if the transcription failed
            transcription_path = os.path.join(VOICE_NOTES_DIR, txt_filename)
            if os.path.exists(transcription_path):
                with open(transcription_path, 'r') as f:
                    transcription = f.read()
                if transcription == "Transcription failed.":
                    wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                    tasks.append(transcribe_and_save(wav_path))
            
            # Check if title generation failed
            title_path = os.path.join(VOICE_NOTES_DIR, title_filename)
            if os.path.exists(title_path):
                with open(title_path, 'r') as f:
                    title_content = f.read()
                if title_content == "Title generation failed.":
                    wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                    tasks.append(transcribe_and_save(wav_path))

    if tasks:
        print(f"Found {len(tasks)} notes to transcribe/title.")
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            if "429" in str(e):
                print("Google API quota exceeded. Please upgrade your plan.")
            else:
                print(f"An error occurred during startup transcription/title generation: {e}")
    else:
        print("No missing transcriptions/titles found.")

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



