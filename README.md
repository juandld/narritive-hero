# Narrative Hero

A web app to record voice notes and turn them into organized, searchable narratives. Notes are automatically transcribed and titled with Gemini (via LangChain), stored as lightweight JSON, and can be combined into narratives.

## Features

- Voice capture and uploads: record in-browser or upload `.wav` files
- Auto transcription and titles: Gemini 2.5 Flash via LangChain
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
- Python 3.10+ and pip (backend)
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
    # Default target is Gemini 2.5 Flash. You can specify human-friendly names
    # (e.g., "gemini 2.5 flash" or "gemini-2.5-flash-002"); the backend
    # normalizes spaces and strips explicit version suffixes.
    # If you need an exact model id with no normalization, set GOOGLE_MODEL_EXACT.
    # GOOGLE_MODEL="gemini 2.5 flash"
    # GOOGLE_MODEL_EXACT="gemini-2.5-flash"
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

    - Optional: Chrome DevTools notice
      - Chrome may request `/.well-known/appspecific/com.chrome.devtools.json` to auto-configure project settings.
      - A minimal file is provided at `frontend/static/.well-known/appspecific/com.chrome.devtools.json` to satisfy this and suppress the notice.

## Project Structure

- `frontend/` SvelteKit app (components for filters, bulk actions, notes, etc.)
- `backend/` FastAPI app
  - `config.py` central paths and env
  - `providers.py` Gemini/OpenAI helpers (rotation + fallbacks)
  - `note_store.py` JSON read/write and metadata helpers
  - `services.py` lean business logic (transcribe/title + notes listing)
  - `main.py` API routes
- `storage/` consolidated app data
  - `storage/voice_notes/` source audio (e.g., `.wav`, `.mp3`)
  - `storage/transcriptions/` one JSON per note (see schema below)
  - `storage/narratives/` saved narratives as `.txt`
- `compose.yaml` Docker Compose services

## Note JSON Schema

Each audio file `storage/voice_notes/<base>.wav` has `storage/transcriptions/<base>.json`:

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

Only JSON files are considered for existing notes. Legacy `.txt`/`.title` files are ignored.

## Backend Behavior

- Transcription providers
  - Primary: Gemini via LangChain (key rotation on 429/quota)
  - Fallback: LangChain OpenAI Whisper/Chat (when configured)
- Startup backfill (non-blocking)
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
  - POST `/api/narratives` → body `[{"filename":"…wav"}, …]` creates concatenated narrative (simple join)
  - POST `/api/narratives/generate` → generate via LLM
    - Body: `{ items: [{ filename: "…wav" }], extra_text?: string, provider?: "auto"|"gemini"|"openai", model?: string, temperature?: number, system?: string }`
    - Uses Gemini (with key rotation) by default and falls back to OpenAI when provider=`auto`
  

## Frontend Highlights

- FiltersBar: date range, topics, min/max seconds, search; Reset and result count
- BulkActions: bottom floating bar for Delete Selected and Create Narrative
- NoteItem: tag chips with compact color picker, preview snippet, expand/collapse
- Config: `frontend/src/lib/config.ts` hosts `BACKEND_URL`

## LangHero (separate app)

- The previous experimental "Learn" route has been split out into its own project: `langhero`.
- Location: `/home/raw/projects/langhero` (same stack and dev/deploy flow as this project).
- Run it the same way (Docker Compose or separate backend/frontend dev). Its frontend root renders the scenario UI and uses its own backend copy of the scenario route.

## Tips

- Use multiple Gemini keys to smooth through quota spikes
- Add OpenAI key for reliable fallback
- To reprocess a note, delete its JSON; backend will recreate it on startup or next upload
- FFmpeg with pydub improves audio format handling (pydub installed; add FFmpeg if needed)

## Testing

- Location and structure
  - All test files and scripts live under `tests/`.
  - Backend: `tests/backend/tests/…` (pytest tests), `tests/backend/test.sh` (runner), `tests/backend/run_smoke_tests.py` (no-deps smoke).
  - Config and dev deps: `tests/backend/pytest.ini`, `tests/backend/requirements-dev.txt`.

- Quick run
  - `bash tests/backend/test.sh` creates/activates a local venv if possible, runs pytest when available, and falls back to smoke tests when offline.
  - Or use Make from within `tests/`: `make -C tests test`.

- Full backend pytest
  - `bash tests/backend/setup_venv.sh`
  - `source tests/backend/.venv/bin/activate`
  - `PYTHONPATH=backend pytest -q tests/backend`

- Run everything
  - `bash tests/run_all.sh` runs backend tests, then frontend tests if available.
