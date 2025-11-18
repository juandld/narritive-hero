"""
Centralized configuration and paths for the backend.

This module exists to keep magic strings and environment reading in one place
so the rest of the codebase can import from here without repeating logic.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Resolve storage directory robustly across dev (repo layout) and container (single-dir app)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# 1) Allow explicit override via env
_STORAGE_DIR_ENV = os.getenv("STORAGE_DIR")
if _STORAGE_DIR_ENV and _STORAGE_DIR_ENV.strip():
    STORAGE_DIR = os.path.abspath(_STORAGE_DIR_ENV.strip())
else:
    # 2) Prefer ./storage next to this file (container layout: /app/storage)
    _cand1 = os.path.join(THIS_DIR, "storage")
    # 3) Fallback: ../storage (repo layout: <repo>/storage)
    _cand2 = os.path.join(os.path.dirname(THIS_DIR), "storage")
    if os.path.isdir(_cand1) or not os.path.isdir(_cand2):
        STORAGE_DIR = _cand1
    else:
        STORAGE_DIR = _cand2
VOICE_NOTES_DIR = os.path.join(STORAGE_DIR, "voice_notes")
TRANSCRIPTS_DIR = os.path.join(STORAGE_DIR, "transcriptions")
NARRATIVES_DIR = os.path.join(STORAGE_DIR, "narratives")
FORMATS_DIR = os.path.join(STORAGE_DIR, "formats")
FOLDERS_DIR = os.path.join(STORAGE_DIR, "folders")
PROGRAMS_DIR = os.path.join(STORAGE_DIR, "programs")
TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip() or None
TELEGRAM_WEBHOOK_SECRET = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip() or None
TELEGRAM_INGEST_TOKEN = (os.getenv("TELEGRAM_INGEST_TOKEN") or "").strip() or None

# Models and providers
def _normalize_google_model(name: str) -> str:
    """Normalize Gemini model names to compatible forms for Google Generative AI.

    Some environments/sdks reject explicit version suffixes like "-002". Prefer
    base or "-latest" variants to maximize compatibility.
    """
    if not name:
        return "gemini-2.5-flash"
    lowered = name.strip().lower().replace(" ", "-")
    # If user provided an explicit version (e.g., -001/-002), prefer -latest
    for suffix in ("-001", "-002", "-003"):
        if lowered.endswith(suffix):
            base = lowered[: -len(suffix)]
            return base + "latest" if base.endswith("-") else base + "-latest"
    return lowered

# Allow an exact override that bypasses normalization.
_GOOGLE_MODEL_EXACT = os.getenv("GOOGLE_MODEL_EXACT")
if _GOOGLE_MODEL_EXACT:
    GOOGLE_MODEL = _GOOGLE_MODEL_EXACT.strip()
else:
    GOOGLE_MODEL = _normalize_google_model(os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"))
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
OPENAI_TITLE_MODEL = os.getenv("OPENAI_TITLE_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_NARRATIVE_MODEL = os.getenv("OPENAI_NARRATIVE_MODEL", "gpt-4o")

# Storage backend selection (filesystem default today; Appwrite planned)
STORE_BACKEND = (os.getenv("STORE_BACKEND") or "filesystem").strip().lower()

# Appwrite configuration (used when STORE_BACKEND == "appwrite")
APPWRITE_ENDPOINT = (os.getenv("APPWRITE_ENDPOINT") or "").strip()
APPWRITE_PROJECT_ID = (os.getenv("APPWRITE_PROJECT_ID") or "").strip()
APPWRITE_API_KEY = (os.getenv("APPWRITE_API_KEY") or "").strip()
APPWRITE_DATABASE_ID = (os.getenv("APPWRITE_DATABASE_ID") or "").strip()
APPWRITE_NOTES_COLLECTION_ID = (os.getenv("APPWRITE_NOTES_COLLECTION_ID") or "").strip()
APPWRITE_NARRATIVES_COLLECTION_ID = (os.getenv("APPWRITE_NARRATIVES_COLLECTION_ID") or "").strip()
APPWRITE_FORMATS_COLLECTION_ID = (os.getenv("APPWRITE_FORMATS_COLLECTION_ID") or "").strip()
APPWRITE_FOLDERS_COLLECTION_ID = (os.getenv("APPWRITE_FOLDERS_COLLECTION_ID") or "").strip()
APPWRITE_PROGRAMS_COLLECTION_ID = (os.getenv("APPWRITE_PROGRAMS_COLLECTION_ID") or "").strip()
APPWRITE_BUCKET_VOICE_NOTES = (os.getenv("APPWRITE_BUCKET_VOICE_NOTES") or "").strip()
APPWRITE_BUCKET_NARRATIVES = (os.getenv("APPWRITE_BUCKET_NARRATIVES") or "").strip()
APPWRITE_AUTH_STRATEGY = (os.getenv("APPWRITE_AUTH_STRATEGY") or "email").strip().lower()

def collect_google_api_keys() -> list[str]:
    keys = []
    for name in [
        "GOOGLE_API_KEY",
        "GOOGLE_API_KEY_1",
        "GOOGLE_API_KEY_2",
        "GOOGLE_API_KEY_3",
    ]:
        val = os.getenv(name)
        if val and val not in keys:
            keys.append(val)
    return keys

def _collect_allowed_origins() -> list[str]:
    """Collect CORS origins from env.

    Priority:
    1) Per-origin variables: ALLOWED_ORIGIN, ALLOWED_ORIGIN_1..N
    2) Backward-compat: ALLOWED_ORIGINS (comma-separated)
    3) Local dev defaults
    """
    origins: list[str] = []
    # 1) Per-origin variables (order by name for consistency)
    keys = [k for k in os.environ.keys() if k == "ALLOWED_ORIGIN" or k.startswith("ALLOWED_ORIGIN_")]
    for key in sorted(keys):
        val = os.getenv(key, "").strip()
        if val and val not in origins:
            origins.append(val)
    if origins:
        return origins

    # 2) Backward-compat comma-separated
    csv = os.getenv("ALLOWED_ORIGINS", "").strip()
    if csv:
        return [o.strip() for o in csv.split(",") if o.strip()]

    # 3) Sensible defaults for local dev (support a few common Vite ports)
    ports = [5173, 5174, 5175, 5176, 5177, 5178, 5179, 5180]
    origins = []
    for p in ports:
        origins.append(f"http://localhost:{p}")
        origins.append(f"http://127.0.0.1:{p}")
    return origins

# Allowed frontend origins for CORS
ALLOWED_ORIGINS = _collect_allowed_origins()


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


LOG_LEVEL = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
LOG_JSON = _parse_bool(os.getenv("LOG_JSON"))
