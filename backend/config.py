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
VOICE_NOTES_DIR = os.path.join(BASE_DIR, "voice_notes")
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "transcriptions")

# Models and providers
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
OPENAI_TITLE_MODEL = os.getenv("OPENAI_TITLE_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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

