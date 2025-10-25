import os
import json
import io
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from base64 import b64encode
import config
import providers
import note_store
import usage_log as usage

# Load environment variables from .env file
load_dotenv()

# Configure providers and models (use centralized, normalized config)
GOOGLE_MODEL = config.GOOGLE_MODEL
OPENAI_TRANSCRIBE_MODEL = config.OPENAI_TRANSCRIBE_MODEL
OPENAI_TITLE_MODEL = config.OPENAI_TITLE_MODEL

# Scenario interaction logic removed from Narrative Hero; lives in LangHero

# Mirror config into module variables so tests can monkeypatch these paths
VOICE_NOTES_DIR = config.VOICE_NOTES_DIR
TRANSCRIPTS_DIR = config.TRANSCRIPTS_DIR

async def transcribe_and_save(wav_path):
    """Transcribes and titles an audio file, saving the results."""
    base_filename = os.path.basename(wav_path)
    ext = os.path.splitext(base_filename)[1].lower().lstrip('.') or 'wav'
    print(f"Starting transcription process for {base_filename}...")
    try:
        # Read audio bytes
        with open(wav_path, "rb") as af:
            audio_bytes = af.read()

        # Transcribe with provider rotation & fallback
        print(f"Transcribing {base_filename} from local file bytes...")
        audio_b64 = b64encode(audio_bytes).decode("utf-8")
        # Choose mime type based on ext
        mime = 'audio/wav'
        if ext in ('webm',):
            mime = 'audio/webm'
        elif ext in ('ogg',):
            mime = 'audio/ogg'
        elif ext in ('mp3',):
            mime = 'audio/mp3'
        elif ext in ('m4a',):
            mime = 'audio/mp4'
        transcription_message = HumanMessage(
            content=[
                {"type": "text", "text": "Transcribe this audio recording."},
                {
                    "type": "file",
                    "source_type": "base64",
                    "mime_type": mime,
                    "data": audio_b64,
                },
            ]
        )
        try:
            # Try Gemini quickly (up to 2 attempts across rotated keys), then fallback
            gemini_ok = False
            last_key_index = None
            for attempt in range(2):
                try:
                    transcription_response, key_index = await asyncio.to_thread(
                        providers.invoke_google, [transcription_message]
                    )
                    last_key_index = key_index
                    transcribed_text = transcription_response.content
                    gemini_ok = True
                    break
                except Exception as ge:
                    print(f"Gemini transcribe attempt {attempt+1} failed for {base_filename}: {ge}")
                    if providers.should_google_fallback(ge):
                        break
                    # non-rate-limit error: try once more, then fallback
                    continue
            if gemini_ok:
                usage.log_usage(
                    event="transcribe",
                    provider="gemini",
                    model=config.GOOGLE_MODEL,
                    key_label=providers.key_label_from_index(last_key_index or 0),
                    status="success",
                )
            else:
                raise RuntimeError("Gemini unavailable, falling back")
        except Exception as e:
            # Fallback to OpenAI Whisper
            print(f"Falling back to Whisper for {base_filename}: {e}")
            transcribed_text = providers.transcribe_with_openai(audio_bytes, file_ext=ext)
            usage.log_usage(
                event="transcribe",
                provider="openai",
                model=config.OPENAI_TRANSCRIBE_MODEL,
                key_label=usage.OPENAI_LABEL,
                status="success",
            )
        print(f"Successfully transcribed {base_filename}.")

        # Generate title
        print(f"Generating title for {base_filename}...")
        try:
            title_message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "Return exactly one short title (5–8 words) for the transcription below. "
                            "Use the same language as the transcription. Do not include quotes, bullets, markdown, or any extra text. "
                            "Output only the title on a single line.\n\n" + transcribed_text
                        ),
                    },
                ]
            )
            # Try Gemini briefly, else fallback to OpenAI title
            gemini_ok = False
            last_key_index = None
            for attempt in range(2):
                try:
                    title_response, key_index = await asyncio.to_thread(
                        providers.invoke_google, [title_message]
                    )
                    last_key_index = key_index
                    title_text = providers.normalize_title_output(title_response.content)
                    gemini_ok = True
                    break
                except Exception as ge:
                    print(f"Gemini title attempt {attempt+1} failed for {base_filename}: {ge}")
                    if providers.should_google_fallback(ge):
                        break
                    continue
            if gemini_ok:
                usage.log_usage(
                    event="title",
                    provider="gemini",
                    model=config.GOOGLE_MODEL,
                    key_label=providers.key_label_from_index(last_key_index or 0),
                    status="success",
                )
            else:
                raise RuntimeError("Gemini unavailable for title")
        except Exception as e:
            try:
                print(f"Falling back to OpenAI title for {base_filename}: {e}")
                title_text = providers.title_with_openai(transcribed_text)
                usage.log_usage(
                    event="title",
                    provider="openai",
                    model=config.OPENAI_TITLE_MODEL,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
            except Exception:
                title_text = "Title generation failed."
        print(f"Successfully generated title for {base_filename}.")

        base_name = os.path.splitext(base_filename)[0]
        audio_ext = os.path.splitext(base_filename)[1].lstrip('.').lower() or 'wav'
        stored_mime = {
            'm4a': 'audio/mp4',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
            'webm': 'audio/webm',
        }.get(audio_ext, f"audio/{audio_ext}" if audio_ext else 'audio/wav')
        metadata = {
            "audio_format": audio_ext,
            "stored_mime": stored_mime,
        }
        if audio_ext == 'm4a':
            metadata.setdefault("sample_rate_hz", 44100)
        elif audio_ext == 'wav':
            metadata.setdefault("sample_rate_hz", 16000)
        existing = None
        try:
            existing, _, _ = note_store.load_note_json(base_name)
        except Exception:
            existing = None
        if isinstance(existing, dict):
            for key in ("content_type", "original_format", "transcoded", "transcoded_from", "sample_rate_hz", "stored_mime"):
                if key in existing and existing[key] is not None:
                    metadata.setdefault(key, existing[key])
        metadata.setdefault("original_format", metadata.get("audio_format"))
        metadata.setdefault("transcoded", False)
        payload = note_store.build_note_payload(base_filename, title_text, transcribed_text, metadata)
        if isinstance(existing, dict):
            if 'folder' in existing and (existing.get('folder') or '').strip() != '':
                payload['folder'] = existing.get('folder')
            if 'tags' in existing and isinstance(existing.get('tags'), list):
                payload['tags'] = existing.get('tags')
        note_store.save_note_json(base_name, payload)
        print(f"Successfully saved transcription and title for {base_filename}.")

    except Exception as e:
        print(f"Error during transcription/titling for {wav_path}: {e}")
        if os.path.exists(wav_path):
            base_name = os.path.splitext(base_filename)[0]
            audio_ext = os.path.splitext(base_filename)[1].lstrip('.').lower() or 'wav'
            stored_mime = {
                'm4a': 'audio/mp4',
                'mp3': 'audio/mpeg',
                'wav': 'audio/wav',
                'ogg': 'audio/ogg',
                'webm': 'audio/webm',
            }.get(audio_ext, f"audio/{audio_ext}" if audio_ext else 'audio/wav')
            metadata = {
                "audio_format": audio_ext,
                "stored_mime": stored_mime,
            }
            if audio_ext == 'm4a':
                metadata.setdefault("sample_rate_hz", 44100)
            elif audio_ext == 'wav':
                metadata.setdefault("sample_rate_hz", 16000)
            existing = None
            try:
                existing, _, _ = note_store.load_note_json(base_name)
            except Exception:
                existing = None
            if isinstance(existing, dict):
                for key in ("content_type", "original_format", "transcoded", "transcoded_from", "sample_rate_hz", "stored_mime"):
                    if key in existing and existing[key] is not None:
                        metadata.setdefault(key, existing[key])
            metadata.setdefault("original_format", metadata.get("audio_format"))
            metadata.setdefault("transcoded", False)
            payload = note_store.build_note_payload(base_filename, "Title generation failed.", "Transcription failed.", metadata)
            try:
                existing = existing or {}
                if isinstance(existing, dict):
                    if 'folder' in existing and (existing.get('folder') or '').strip() != '':
                        payload['folder'] = existing.get('folder')
                    if 'tags' in existing and isinstance(existing.get('tags'), list):
                        payload['tags'] = existing.get('tags')
            except Exception:
                pass
            note_store.save_note_json(base_name, payload)

# Removed unused helpers and scenario-related functions to reduce complexity

def get_notes():
    """Lists all notes with their details, including date, topics, and length.

    Combines:
      - Notes with audio files under VOICE_NOTES_DIR
      - Text-only notes that exist as JSONs under TRANSCRIPTS_DIR
    """
    notes: list[dict] = []

    # Ensure dirs exist
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
    os.makedirs(VOICE_NOTES_DIR, exist_ok=True)

    AUDIO_EXTS = ('.wav', '.ogg', '.webm', '.m4a', '.mp3')
    # First: audio-backed notes
    wav_files = [f for f in os.listdir(VOICE_NOTES_DIR) if f.lower().endswith(AUDIO_EXTS)]
    wav_files.sort(key=lambda f: os.path.getmtime(os.path.join(VOICE_NOTES_DIR, f)), reverse=True)
    seen_bases: set[str] = set()
    for filename in wav_files:
        base_filename = os.path.splitext(filename)[0]
        seen_bases.add(base_filename)
        audio_path = os.path.join(VOICE_NOTES_DIR, filename)
        data, transcription, title = note_store.load_note_json(base_filename)
        if data is None:
            # JSON not yet created (transcription pending). Return lightweight metadata
            mtime = os.path.getmtime(audio_path)
            date_str = __import__('datetime').datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            length_sec = note_store.audio_length_seconds(audio_path)
            audio_ext = os.path.splitext(filename)[1].lstrip('.').lower() or 'wav'
            stored_mime = {
                'm4a': 'audio/mp4',
                'mp3': 'audio/mpeg',
                'wav': 'audio/wav',
                'ogg': 'audio/ogg',
                'webm': 'audio/webm',
            }.get(audio_ext, f"audio/{audio_ext}" if audio_ext else 'audio/wav')
            notes.append({
                "filename": filename,
                "transcription": transcription,  # likely None
                "title": (title or base_filename),
                "date": date_str,
                "created_at": __import__('datetime').datetime.fromtimestamp(mtime).isoformat(),
                "created_ts": int(mtime * 1000),
                "length_seconds": length_sec,
                "topics": [],
                "folder": "",
                "tags": [],
                "audio_format": audio_ext,
                "stored_mime": stored_mime,
                "original_format": audio_ext,
                "transcoded": False,
            })
            continue
        else:
            data = note_store.ensure_metadata_in_json(base_filename, data)

        # Normalize title: avoid placeholder values
        _title = (title or data.get("title") or "").strip()
        if not _title or _title.lower() in ("untitled", "title generation failed."):
            _title = base_filename
        notes.append({
            "filename": data.get("filename") or filename,
            "transcription": transcription,
            "title": _title,
            "date": data.get("date"),
            "created_at": data.get("created_at"),
            "created_ts": data.get("created_ts"),
            "length_seconds": data.get("length_seconds"),
            "topics": data.get("topics", []),
            "language": data.get("language", "und"),
            "folder": data.get("folder", ""),
            "tags": data.get("tags", []),
        })

    # Second: text-only notes (JSONs with no matching audio base)
    for fn in sorted(os.listdir(config.TRANSCRIPTS_DIR)):
        if not fn.endswith('.json'):
            continue
        base = os.path.splitext(fn)[0]
        if base in seen_bases:
            continue  # already accounted for by audio-backed loop
        try:
            with open(os.path.join(config.TRANSCRIPTS_DIR, fn), 'r') as f:
                data = json.load(f)
            # Ensure JSON has expected metadata (language, topics, etc.)
            try:
                data = note_store.ensure_metadata_in_json(base, data)
            except Exception:
                pass
            # Use JSON content directly
            _title2 = (str(data.get("title") or "")).strip() or base
            if _title2.lower() in ("untitled", "title generation failed."):
                _title2 = base
            notes.append({
                "filename": str(data.get("filename") or base + ".txt"),
                "transcription": data.get("transcription"),
                "title": _title2,
                "date": data.get("date"),
                "created_at": data.get("created_at"),
                "created_ts": data.get("created_ts"),
                "length_seconds": data.get("length_seconds"),
                "topics": data.get("topics", []),
                "language": data.get("language", "und"),
                "folder": data.get("folder", ""),
                "tags": data.get("tags", []),
            })
        except Exception:
            continue

    return notes
