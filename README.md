# Narrative Hero

A web app to record voice notes and turn them into organized, searchable narratives. Notes are automatically transcribed and titled with Gemini (via LangChain), stored as lightweight JSON, and can be combined into narratives.

## Features

- Voice capture and uploads: record in-browser or upload `.wav` files
- Auto transcription and titles: Gemini 1.5 Flash via LangChain
- Resilient providers: rotate multiple Gemini keys and fallback to OpenAI Whisper/Chat through LangChain
- JSON metadata per note: title, transcription, date, duration, topics, tags
- Filtering & search: by date range, topics, duration, and free-text query
- Tags: add your own color-coded tags (with last-used color remembered)
- Bulk actions: delete selected notes, create narratives from selection
- Narratives drawer: list, open, and delete generated narratives

## Tech Stack

- Frontend: SvelteKit (TypeScript)
- Backend: FastAPI (Python) + LangChain (Gemini/OpenAI)
- Containerization: Docker, Docker Compose

## Prerequisites

- Docker and Docker Compose (optional)
- Node.js and npm (frontend)
- Python 3.9+ and pip (backend)
- API keys: Google AI (Gemini). Optional: OpenAI (fallback)

## Running the Project

### Production (using Docker)

This is the recommended way to run the project.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd narrative-hero
    ```

2.  **Create a `.env` file (backend):**
    ```ini
    # Primary Gemini key
    GOOGLE_API_KEY="your-gemini-key-A"
    # Optional extra Gemini keys for rotation
    GOOGLE_API_KEY_1="your-gemini-key-B"
    GOOGLE_API_KEY_2="your-gemini-key-C"
    GOOGLE_API_KEY_3="your-gemini-key-D"

    # Optional: OpenAI fallback (LangChain)
    OPENAI_API_KEY="your-openai-key"

    # Optional: override models
    # GOOGLE_MODEL="gemini-1.5-flash"
    # OPENAI_TRANSCRIBE_MODEL="whisper-1"
    # OPENAI_TITLE_MODEL="gpt-4o-mini"
    ```

3.  **Build and run the application with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

4.  **Access the application:**
    The frontend will be available at `http://localhost`.

### Local Development

For development, you can run the frontend and backend services separately.

#### Backend

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create `.env` (see example above).**

3.  **Run the development script:**
    ```bash
    ./dev.sh
    ```
    This script will automatically create a virtual environment, install dependencies if needed, and start the backend server at `http://localhost:8000`.

#### Frontend

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the frontend development server:**
    ```bash
    npm run dev
    ```
    The frontend will be available at `http://localhost:5173`.

## Project Structure

- `frontend/` SvelteKit app (components for filters, bulk actions, notes, etc.)
- `backend/` FastAPI app
  - `config.py` central paths and env
  - `providers.py` Gemini/OpenAI helpers (rotation + fallbacks)
  - `note_store.py` JSON read/write and metadata helpers
  - `services.py` lean business logic (transcribe/title + notes listing)
  - `main.py` API routes
- `voice_notes/` source audio `.wav` files
- `transcriptions/` one JSON per note (see schema below)
- `narratives/` saved narratives as `.txt`
- `compose.yaml` Docker Compose services

## Note JSON Schema

Each audio file `voice_notes/<base>.wav` has `transcriptions/<base>.json`:

```json
{
  "filename": "20250923_140154.wav",
  "title": "Quick standup notes",
  "transcription": "We discussed…",
  "date": "2025-09-23",
  "length_seconds": 42.5,
  "topics": ["standup", "team", "progress"],
  "tags": [{ "label": "work", "color": "#3B82F6" }]
}
```

On startup, any legacy `.txt`/`.title` are consolidated into JSON. Missing metadata is backfilled.

## Backend Behavior

- Transcription providers
  - Primary: Gemini via LangChain (key rotation on 429/quota)
  - Fallback: LangChain OpenAI Whisper/Chat (when configured)
- Startup backfill (non-blocking)
  - Migrates legacy files to JSON
  - Creates JSON for `.wav` lacking one
  - Does not re-transcribe if JSON exists (delete JSON to force refresh)
- Usage logging
  - Daily JSONL and weekly JSON in `backend/usage/` (git-ignored)

## API Overview

- Notes
  - GET `/api/notes` → list with metadata (title, transcription, date, length, topics, tags)
  - POST `/api/notes` (multipart: `file`) → save audio; transcribe/title in background
  - DELETE `/api/notes/{filename}` → delete audio + JSON
  - PATCH `/api/notes/{filename}/tags` → `{ "tags": [{"label":"…","color":"#…"}] }`
- Narratives
  - GET `/api/narratives` → list filenames
  - GET `/api/narratives/{filename}` → `{ content }`
  - DELETE `/api/narratives/{filename}`
  - POST `/api/narratives` → body `[{"filename":"…wav"}, …]` creates concatenated narrative
- Scenarios (demo)
  - POST `/narrative/interaction` → simple yes/no branching using speech intent

## Frontend Highlights

- FiltersBar: date range, topics, min/max seconds, search; Reset and result count
- BulkActions: bottom floating bar for Delete Selected and Create Narrative
- NoteItem: tag chips with compact color picker, preview snippet, expand/collapse
- Config: `frontend/src/lib/config.ts` hosts `BACKEND_URL`

## Tips

- Use multiple Gemini keys to smooth through quota spikes
- Add OpenAI key for reliable fallback
- To reprocess a note, delete its JSON; backend will recreate it on startup or next upload
- FFmpeg with pydub improves audio format handling (pydub installed; add FFmpeg if needed)
