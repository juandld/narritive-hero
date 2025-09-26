"""
Centralized configuration and paths for the backend.

This module exists to keep magic strings and environment reading in one place
so the rest of the codebase can import from here without repeating logic.
"""

import os
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Base application directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Consolidate storage under a single folder
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
VOICE_NOTES_DIR = os.path.join(STORAGE_DIR, "voice_notes")
TRANSCRIPTS_DIR = os.path.join(STORAGE_DIR, "transcriptions")
NARRATIVES_DIR = os.path.join(STORAGE_DIR, "narratives")

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
