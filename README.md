# Narrative Hero

A web app to capture voice notes and turn them into organized, searchable narratives. Notes are automatically transcribed and titled (Gemini via LangChain, with OpenAI fallbacks), stored as lightweight JSON, and can be combined into narratives or used to generate new ones with an LLM.

## Quick Start (TL;DR)

- Backend: copy `backend/.env.example` to `backend/.env` and add your keys.
- Dev mode:
  - In one terminal: `cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
  - In another: `cd frontend && npm install && npm run dev`
  - Open `http://localhost:5173`
- Docker (all-in-one): `docker compose up --build` then open `http://localhost` (backend at `http://localhost:8000`).
- Add notes: click Upload (Topbar), drag & drop audio anywhere, use Start Recording, or click New Text Note to paste an existing transcript.
- Expand/collapse text: click the ▼/▲ toggle within a note card. You can also switch views (List/Compact/Grid) from the Topbar.

## Features

- Voice capture and uploads: record in-browser or upload `.wav` files
- Auto transcription and titles: Gemini 2.5 Flash via LangChain (key rotation)
- Resilient providers: rotate multiple Gemini keys and fallback to OpenAI Whisper/Chat
- JSON metadata per note: title, transcription, date, duration, topics, tags
- Filtering & search: by date range, topics, duration, and free-text query
- Tags: add your own color-coded tags (with last-used color remembered)
- Bulk actions: delete selected notes, create narratives from selection
- Narratives: list, open, delete, assign folders; generate or iterate with formats

## Data & Layout

- Storage (local by default):
  - `storage/voice_notes/` — uploaded/recorded audio
  - `storage/transcriptions/` — one JSON per note (metadata + text)
  - `storage/narratives/` — generated narratives (`.txt`)
- Frontend dev server: `http://localhost:5173`
- Narratives page: `http://localhost:5173/narratives`
- Backend dev server: `http://localhost:8000`
- Docker: frontend on `:80`, backend on `:8000`
- Compose volumes: voice notes, transcriptions, narratives mapped to `./storage/...` on host

## Tech Stack

- Frontend: SvelteKit (TypeScript)
- Backend: FastAPI (Python) + LangChain (Gemini/OpenAI)
- Containerization: Docker, Docker Compose

## Prerequisites

- Docker and Docker Compose (optional)
- Node.js and npm (frontend)
- Python 3.10+ and pip (backend)
- API keys: Google AI (Gemini). Optional: OpenAI (fallbacks)

## Running the Project

### Production (using Docker)

This is the recommended way to run the project.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd narritive-hero
    ```

2.  **Create a `.env` file (backend):**
   You can start from the example file.
    ```ini
    # Copy example and edit values
    # cp backend/.env.example backend/.env

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
    # If you need an exact model id (no normalization), set GOOGLE_MODEL_EXACT.
    # GOOGLE_MODEL="gemini 2.5 flash"
    # GOOGLE_MODEL_EXACT="gemini-2.5-flash"
    # OPENAI_TRANSCRIBE_MODEL="whisper-1"
    # OPENAI_TITLE_MODEL="gpt-4o-mini"
    # OPENAI_NARRATIVE_MODEL="gpt-4o"
    ```

3.  **Build and run the application with Docker Compose:**
    ```bash
    # Compose V2 syntax
    docker compose up --build
    # (Older Docker installs may use: docker-compose up --build)
    ```

4.  **Access the application:**
    The frontend will be available at `http://localhost`.
    - Backend API: `http://localhost:8000` (FastAPI docs at `http://localhost:8000/docs`)
    - Ports: frontend `80`, backend `8000` (see `compose.yaml`)

### Local Development

For development, you can run the frontend and backend services separately, or use the root helper script to run both.

#### Backend

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create `.env` (see example above).**

3.  **Create a virtualenv (first time only):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

4.  **Run the development server:**
    ```bash
    # Option A: use the helper script (expects an existing venv)
    ./dev.sh

    # Option B: run directly with uvicorn
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The helper script assumes you've already created and activated `venv`; it installs dependencies and starts the backend at `http://localhost:8000`.

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

#### Run both (convenience)

From the repo root you can start both dev servers together:

```bash
./dev.sh
```
This launches the Svelte dev server and the FastAPI dev server concurrently.

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
  - `storage/formats/` saved generation formats (JSON)
  - `storage/folders/` folders registry (JSON)
- `compose.yaml` Docker Compose services

Notes:
- In Docker, the frontend is served as static files via Nginx and the browser calls the backend at `http://localhost:8000` directly (published from the backend container). No proxy is required.
- Only `voice_notes`, `transcriptions`, and `narratives` are volume‑mapped by default. If you need `formats` and `folders` to persist across rebuilds, add volume mappings for `./storage/formats` and `./storage/folders` in `compose.yaml`.

## Environment Variables

Backend reads from `backend/.env` (copy from `.env.example`). Common keys:

- `GOOGLE_API_KEY`, `GOOGLE_API_KEY_1..3` — Gemini API keys (rotation supported)
- `GOOGLE_MODEL` — optional model override (normalized, e.g. `gemini 2.5 flash`)
- `GOOGLE_MODEL_EXACT` — exact Gemini model id (disables normalization)
- `OPENAI_API_KEY` — optional fallback for Whisper/Chat
- `OPENAI_TRANSCRIBE_MODEL` — default `whisper-1`
- `OPENAI_TITLE_MODEL` — default `gpt-4o-mini`
- `OPENAI_NARRATIVE_MODEL` — default `gpt-4o`

Frontend config: `frontend/src/lib/config.ts` → `BACKEND_URL` (default `http://localhost:8000`).

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
  "language": "en",
  "folder": "",
  "tags": [{ "label": "work", "color": "#3B82F6" }]
}
```

Only JSON files are considered for existing notes. Legacy `.txt`/`.title` files are ignored.

<!-- duplicate Testing section removed; consolidated below -->

## Backend Behavior

- Transcription providers
  - Primary: Gemini via LangChain (key rotation on 429/quota)
  - Fallback: LangChain OpenAI Whisper/Chat (when configured)
- Startup backfill (non-blocking)
  - Creates JSON for `.wav` lacking one
  - Does not re-transcribe if JSON exists (delete JSON to force refresh)
  - Backfills metadata (topics, tags, folder, language) into existing JSONs so sorting/filtering work consistently
- Usage logging
  - Daily JSONL and weekly JSON in `backend/usage/` (git-ignored)

## API Overview

- Notes
  - GET `/api/notes` → list with metadata (title, transcription, date, length, topics, tags)
  - POST `/api/notes` (multipart: `file`) → save audio; transcribe/title in background
  - POST `/api/notes/text` (JSON: `{ transcription, title?, folder?, date?, tags? }`) → create a text-only note (no audio). If `title` is omitted, the backend generates one via Gemini with OpenAI fallback.
  - POST `/api/notes/{filename}/retry` → requeue background transcribe/title for an existing note
  - DELETE `/api/notes/{filename}` → delete audio + JSON
  - PATCH `/api/notes/{filename}/tags` → `{ "tags": [{"label":"…","color":"#…"}] }`
  - PATCH `/api/notes/{filename}/folder` → `{ "folder": "…" }` assign or clear a folder
- Narratives
  - GET `/api/narratives` → list filenames
  - GET `/api/narratives/{filename}` → `{ content, title? }`
  - DELETE `/api/narratives/{filename}`
  - POST `/api/narratives` → body `[{"filename":"…wav"}, …]` creates concatenated narrative (simple join)
  - POST `/api/narratives/generate` → generate via LLM (auto-titles narrative and saves metadata)
  - GET `/api/narratives/list` → list `{ filename, title?, folder }` for all narratives
  - GET `/api/narratives/thread/{filename}` → return version thread for a narrative `{ files, index }`
  - PATCH `/api/narratives/{filename}/folder` → set a folder for a narrative `{ folder }`
  - GET `/api/narratives/folders` → list narrative folders `{ name, count }`
    - Body: `{ items: [{ filename: "…wav" }], extra_text?: string, provider?: "auto"|"gemini"|"openai", model?: string, temperature?: number, system?: string }`
    - Includes each note's `date` alongside its `title` and text in the prompt context.
    - Uses Gemini (with key rotation) by default and falls back to OpenAI when provider=`auto`.

- Formats (optional saved prompts for generation)
  - GET `/api/formats` → list saved formats `{ id, title, prompt }`
  - POST `/api/formats` → create/update `{ title, prompt, id? }` → `{ id }`
  - DELETE `/api/formats/{id}` → remove a saved format

- Folders
  - GET `/api/folders` → list `{ name, count }`
  - POST `/api/folders` → create `{ name }`
  - DELETE `/api/folders/{name}` → remove folder and delete notes within

- Static
  - `/voice_notes/{filename}` → serves uploaded audio files

Open API docs: visit `http://localhost:8000/docs`.
  

## Frontend Highlights

- FiltersBar: date range, topics, min/max seconds, search; Reset and result count
- BulkActions: bottom floating bar for Delete Selected and Create Narrative
- NoteItem: tag chips with compact color picker, preview snippet, expand/collapse
- Config: `frontend/src/lib/config.ts` hosts `BACKEND_URL`

Default `BACKEND_URL` is `http://localhost:8000`. When using Docker Compose, this is correct because requests originate from the browser, not inside the container. Use the top bar “Narratives” to open the full narratives page.

## Troubleshooting

- Can’t expand text? Click the ▼ button inside the note card to toggle the full transcription. In Compact view, the same toggle applies per note.
- Upload works but no text appears: transcription runs in the background; refresh after a moment. If it failed, try “Retry” via `POST /api/notes/{filename}/retry` or re-upload.
- 429/quota errors: the backend rotates Gemini keys automatically and falls back to OpenAI when configured.
- Ports busy: adjust mappings in `compose.yaml` or run dev servers on different ports.
- Non‑WAV audio requires FFmpeg at runtime for duration detection with pydub (Docker image installs FFmpeg; for local dev, install it via your OS package manager).

## Frontend Notes

Some legacy components/exports are present and appear unused based on a static search of imports/references in `frontend/src`.

- Components
  - `frontend/src/lib/components/FileUpload.svelte` — superseded by the Topbar upload button and `pageDrop` action.
  - `frontend/src/lib/components/FolderSidebar.svelte` — replaced by folder chips/cards within `NotesList.svelte`.
  - `frontend/src/lib/components/RecordingControls.svelte` — replaced by `Topbar.svelte` and `uiApp` store actions.
- Unused exports (safe to keep, but not referenced)
  - `frontend/src/lib/services/appActions.ts: deleteNotes`
  - `frontend/src/lib/stores/notes.ts: notesActions.refresh`
  - `frontend/src/lib/stores/folders.ts: folderActions.refresh`

Notes
- Detection method: static search across `frontend/src`.
- Caveat: dynamic usage (code-splitting or string imports) would not be detected.
- If you want, we can remove these in a follow‑up cleanup.

<!-- Former experimental route (LangHero) has been removed from this app; scenario functionality lives in a separate project and is not required here. -->

<!-- duplicate Testing/Troubleshooting sections removed; content merged into single sections -->

## Tips

- Use multiple Gemini keys to smooth through quota spikes
- Add OpenAI key for reliable fallback
- To reprocess a note, delete its JSON; backend will recreate it on startup or next upload
- FFmpeg with pydub improves audio format handling (Docker installs FFmpeg; add it locally if needed)

## Testing

- Location and structure
  - All test files and scripts live under `tests/`.
  - Backend: `tests/backend/tests/…` (pytest tests), `tests/backend/test.sh` (runner), `tests/backend/run_smoke_tests.py` (no-deps smoke).
  - Config and dev deps: `tests/backend/pytest.ini`, `tests/backend/requirements-dev.txt`.
  - Tests create temp dirs and stub external providers; no real API calls.

- Quick run
  - `bash tests/backend/test.sh` creates/activates a local venv if possible, runs pytest when available, and falls back to smoke tests when offline.
  - Or use Make from within `tests/`: `make -C tests test`.

- Full backend pytest
  - `bash tests/backend/setup_venv.sh`
  - `source tests/backend/.venv/bin/activate`
  - `PYTHONPATH=backend pytest -q tests/backend`

- Run everything
  - `bash tests/run_all.sh` runs backend tests, then frontend tests if available.
