"""
Note storage helpers: read/write JSON, compute metadata, and lightweight NLP.

Pure functions live here to keep services small and easy to maintain.
"""

from __future__ import annotations

import json
import os
import wave
import contextlib
from datetime import datetime
from typing import Any, Dict, Tuple

import config


def audio_length_seconds(path: str) -> float | None:
    try:
        with contextlib.closing(wave.open(path, 'rb')) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return round(frames / float(rate), 2) if rate else None
    except Exception:
        return None


STOPWORDS = set(
    "the a an and or but for with without on in at to from of by this that those these is are was were be been being i you he she it we they them me my your our their as not just into over under again more most some any few many much very can could should would".split()
)


def infer_topics(text: str | None, title: str | None) -> list[str]:
    source = (title or "").strip() or (text or "").strip()
    if not source:
        return []
    import re

    words = re.findall(r"[A-Za-z]{3,}", source.lower())
    words = [w for w in words if w not in STOPWORDS]
    freq: Dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    return sorted(freq, key=lambda k: (-freq[k], k))[:3]


def note_json_path(base_filename: str) -> str:
    return os.path.join(config.TRANSCRIPTS_DIR, f"{base_filename}.json")


def build_note_payload(audio_filename: str, title: str, transcription: str) -> dict:
    """Build note JSON payload using the actual audio filename (with extension)."""
    audio_path = os.path.join(config.VOICE_NOTES_DIR, audio_filename)
    mtime = os.path.getmtime(audio_path) if os.path.exists(audio_path) else None
    date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d') if mtime else None
    length_sec = audio_length_seconds(audio_path) if mtime else None
    topics = infer_topics(transcription, title)
    return {
        "filename": audio_filename,
        "title": title,
        "transcription": transcription,
        "date": date_str,
        "length_seconds": length_sec,
        "topics": topics,
        "tags": [],
    }


def load_note_json(base_filename: str) -> Tuple[dict | None, str | None, str | None]:
    """Return (data, transcription, title) from JSON if exists, else (None, None, None)."""
    path = note_json_path(base_filename)
    if not os.path.exists(path):
        return None, None, None
    try:
        with open(path, 'r') as jf:
            data = json.load(jf)
        return data, data.get("transcription"), data.get("title")
    except Exception:
        return None, None, None


def ensure_metadata_in_json(base_filename: str, data: dict) -> dict:
    """Ensure date/length/topics/tags fields exist and persist if updated."""
    audio_path = os.path.join(config.VOICE_NOTES_DIR, f"{base_filename}.wav")
    updated = False
    if not data.get("date"):
        mtime = os.path.getmtime(audio_path)
        data["date"] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        updated = True
    if data.get("length_seconds") is None:
        data["length_seconds"] = audio_length_seconds(audio_path)
        updated = True
    if not isinstance(data.get("topics"), list):
        data["topics"] = infer_topics(data.get("transcription"), data.get("title"))
        updated = True
    if not isinstance(data.get("tags"), list):
        data["tags"] = []
        updated = True
    if updated:
        save_note_json(base_filename, data)
    return data


def save_note_json(base_filename: str, payload: dict) -> None:
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
    with open(note_json_path(base_filename), 'w') as jf:
        json.dump(payload, jf, ensure_ascii=False)
