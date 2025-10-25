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
from typing import Any, Dict, Tuple, Optional

import config


def audio_length_seconds(path: str) -> Optional[float]:
    """Return audio length in seconds for common formats.

    Uses wave module for WAV; falls back to pydub (ffmpeg) for other types.
    """
    try:
        # Prefer the lightweight wave reader for .wav files
        if path.lower().endswith('.wav'):
            with contextlib.closing(wave.open(path, 'rb')) as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return round(frames / float(rate), 2) if rate else None
        # Non-wav: try pydub if available
        try:
            from pydub import AudioSegment
            seg = AudioSegment.from_file(path)
            return round(len(seg) / 1000.0, 2)
        except Exception:
            return None
    except Exception:
        return None


STOPWORDS = set(
    "the a an and or but for with without on in at to from of by this that those these is are was were be been being i you he she it we they them me my your our their as not just into over under again more most some any few many much very can could should would".split()
)

def infer_language(text: str | None, title: str | None = None) -> str:
    """Very lightweight language inference.

    - Detects scripts (CJK, Cyrillic, Arabic, Hebrew, Devanagari) by Unicode ranges
    - For Latin languages, uses small stopword probes across a handful of languages
    Returns a BCP-47-ish short code (e.g., 'en', 'es') or 'und' if unknown.
    """
    src = (text or '').strip() or (title or '').strip()
    if not src:
        return 'und'
    # Script detection by ranges
    for ch in src:
        o = ord(ch)
        if 0x3040 <= o <= 0x30FF:  # Hiragana/Katakana
            return 'ja'
        if 0x4E00 <= o <= 0x9FFF:  # CJK Unified Ideographs (common for zh)
            return 'zh'
        if 0xAC00 <= o <= 0xD7AF:  # Hangul
            return 'ko'
        if 0x0400 <= o <= 0x04FF:  # Cyrillic
            return 'ru'
        if 0x0590 <= o <= 0x05FF:  # Hebrew
            return 'he'
        if 0x0600 <= o <= 0x06FF:  # Arabic
            return 'ar'
        if 0x0900 <= o <= 0x097F:  # Devanagari
            return 'hi'

    # Latin-based heuristic using tiny stopword sets
    import re
    tokens = [t for t in re.findall(r"[A-Za-z]{2,}", src.lower()) if t]
    if not tokens:
        return 'und'
    SW = {
        'en': {'the','and','to','of','in','that','for','with','on','is','it'},
        'es': {'el','la','de','y','en','que','para','con','los','las','es'},
        'fr': {'le','la','et','de','des','en','que','pour','avec','les','est'},
        'de': {'der','die','und','in','den','von','zu','mit','das','ist'},
        'it': {'il','la','e','di','che','per','con','le','gli','è'},
        'pt': {'o','a','e','de','que','para','com','os','as','é'},
        'nl': {'de','het','en','van','in','met','voor','op','is'},
        'sv': {'och','att','det','som','i','på','för','är'},
        'tr': {'ve','bir','bu','için','ile','de','da','şu','olan'},
        'pl': {'i','w','na','że','z','do','jest','się','po'},
        'ro': {'și','în','de','la','cu','este','pentru','pe'},
        'cs': {'a','že','se','v','na','s','pro','je'},
    }
    scores: dict[str,int] = {k:0 for k in SW.keys()}
    for t in tokens:
        for lang, sw in SW.items():
            if t in sw:
                scores[lang] += 1
    # pick max
    best = max(scores.items(), key=lambda kv: kv[1] if kv[1] is not None else 0)
    return best[0] if best[1] > 0 else 'und'


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


def build_note_payload(audio_filename: str, title: str, transcription: str, metadata: Optional[dict] = None) -> dict:
    """Build note JSON payload using the actual audio filename (with extension)."""
    audio_path = os.path.join(config.VOICE_NOTES_DIR, audio_filename)
    mtime = os.path.getmtime(audio_path) if os.path.exists(audio_path) else None
    date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d') if mtime else None
    created_ts = int(mtime * 1000) if mtime else int(datetime.now().timestamp() * 1000)
    created_at = datetime.fromtimestamp(mtime).isoformat() if mtime else datetime.now().isoformat()
    length_sec = audio_length_seconds(audio_path) if mtime else None
    topics = infer_topics(transcription, title)
    language = infer_language(transcription, title)
    payload = {
        "filename": audio_filename,
        "title": title,
        "transcription": transcription,
        "date": date_str,
        "created_at": created_at,
        "created_ts": created_ts,
        "length_seconds": length_sec,
        "topics": topics,
        "language": language,
        "folder": "",
        "tags": [],
    }
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                payload[key] = value
    return payload


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


def _find_audio_path(base_filename: str, data: dict) -> Optional[str]:
    """Locate the actual audio file for a note base name.

    Prefer the filename embedded in JSON (data['filename']). Fallback to
    scanning the voice notes directory for any supported extension.
    """
    # 1) Prefer JSON's filename, if present
    fname = (data or {}).get('filename')
    if isinstance(fname, str) and fname:
        p = os.path.join(config.VOICE_NOTES_DIR, fname)
        if os.path.exists(p):
            return p
    # 2) Scan for matching base with any known extension
    AUDIO_EXTS = ('.wav', '.ogg', '.webm', '.m4a', '.mp3')
    for ext in AUDIO_EXTS:
        p = os.path.join(config.VOICE_NOTES_DIR, f"{base_filename}{ext}")
        if os.path.exists(p):
            return p
    return None


def ensure_metadata_in_json(base_filename: str, data: dict) -> dict:
    """Ensure date/length/topics/tags fields exist and persist if updated."""
    audio_path = _find_audio_path(base_filename, data)
    updated = False
    jp = note_json_path(base_filename)
    if audio_path and os.path.exists(audio_path):
        audio_ext = os.path.splitext(audio_path)[1].lstrip('.').lower() or 'wav'
        stored_mime = {
            'm4a': 'audio/mp4',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
            'webm': 'audio/webm',
        }.get(audio_ext, f"audio/{audio_ext}" if audio_ext else 'audio/wav')
        if not data.get("audio_format"):
            data["audio_format"] = audio_ext
            updated = True
        if not data.get("stored_mime"):
            data["stored_mime"] = stored_mime
            updated = True
        if not data.get("original_format"):
            data["original_format"] = data.get("audio_format") or audio_ext
            updated = True
        if "transcoded" not in data:
            data["transcoded"] = False
            updated = True
        if not data.get("upload_extension"):
            data["upload_extension"] = audio_ext
            updated = True
        if not data.get("date"):
            mtime = os.path.getmtime(audio_path)
            data["date"] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            updated = True
        # Ensure created_at/created_ts from audio mtime if missing
        if not data.get("created_ts") or not isinstance(data.get("created_ts"), (int, float)):
            try:
                mtime = os.path.getmtime(audio_path)
                data["created_ts"] = int(mtime * 1000)
                data["created_at"] = datetime.fromtimestamp(mtime).isoformat()
                updated = True
            except Exception:
                pass
        if data.get("length_seconds") is None:
            data["length_seconds"] = audio_length_seconds(audio_path)
            updated = True
    # If still no date and JSON exists, use JSON file mtime as a fallback (e.g., text-only notes)
    if not data.get("date") and os.path.exists(jp):
        try:
            mtime = os.path.getmtime(jp)
            data["date"] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            updated = True
        except Exception:
            pass
    # If created ts/at missing and we have JSON mtime, set from it
    if (not data.get("created_ts") or not isinstance(data.get("created_ts"), (int, float))) and os.path.exists(jp):
        try:
            mtime = os.path.getmtime(jp)
            data["created_ts"] = int(mtime * 1000)
            data["created_at"] = datetime.fromtimestamp(mtime).isoformat()
            updated = True
        except Exception:
            pass
    if not isinstance(data.get("topics"), list):
        data["topics"] = infer_topics(data.get("transcription"), data.get("title"))
        updated = True
    # Ensure language present
    if not isinstance(data.get("language"), str) or not data.get("language"):
        data["language"] = infer_language(data.get("transcription"), data.get("title"))
        updated = True
    if not isinstance(data.get("tags"), list):
        data["tags"] = []
        updated = True
    # Ensure folder string key exists
    if not isinstance(data.get("folder"), str):
        data["folder"] = ""
        updated = True
    if updated:
        save_note_json(base_filename, data)
    return data


def save_note_json(base_filename: str, payload: dict) -> None:
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
    with open(note_json_path(base_filename), 'w') as jf:
        json.dump(payload, jf, ensure_ascii=False)
