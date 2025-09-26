import os
import json
import uuid
import io
import asyncio
import wave
import contextlib
from datetime import datetime
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders.parsers.audio import OpenAIWhisperParser
from base64 import b64encode
from typing import List, Optional, Tuple
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

def _collect_google_api_keys() -> List[str]:
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

GOOGLE_KEYS = _collect_google_api_keys()
GOOGLE_LLMS: List[ChatGoogleGenerativeAI] = [
    ChatGoogleGenerativeAI(model=GOOGLE_MODEL, api_key=k) for k in GOOGLE_KEYS
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _is_rate_limit_error(e: Exception) -> bool:
    s = str(e).lower()
    return (
        "429" in s
        or "rate limit" in s
        or "quota" in s
        or "exceeded your current quota" in s
    )

def _should_google_fallback(e: Exception) -> bool:
    s = str(e).lower()
    return _is_rate_limit_error(e) or (
        "no google gemini api keys configured" in s
        or "unauthorized" in s
        or "permission" in s
        or "invalid api key" in s
        or "not found" in s
        or "publisher model" in s
    )

async def _ainvoke_google(messages: List[HumanMessage]) -> Tuple[object, int]:
    last_err: Optional[Exception] = None
    for idx, llm in enumerate(GOOGLE_LLMS):
        try:
            return await llm.ainvoke(messages), idx
        except Exception as e:
            last_err = e
            if _is_rate_limit_error(e):
                continue
            else:
                # Non-rate-limit error, try next key anyway
                continue
    if last_err:
        raise last_err
    raise RuntimeError("No Google Gemini API keys configured.")

def _invoke_google(messages: List[HumanMessage]) -> Tuple[object, int]:
    last_err: Optional[Exception] = None
    for idx, llm in enumerate(GOOGLE_LLMS):
        try:
            return llm.invoke(messages, max_retries=0), idx
        except Exception as e:
            last_err = e
            if _is_rate_limit_error(e):
                continue
            else:
                continue
    if last_err:
        raise last_err
    raise RuntimeError("No Google Gemini API keys configured.")

def _transcribe_with_openai(audio_bytes: bytes, file_ext: str = "wav") -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    # Use LangChain community OpenAI Whisper parser
    parser = OpenAIWhisperParser(
        api_key=OPENAI_API_KEY,
        model=OPENAI_TRANSCRIBE_MODEL,
    )
    # Try direct bytes; if parser requires a file path, fall back to temp file
    try:
        result = parser.parse(audio_bytes)  # type: ignore[arg-type]
    except Exception:
        tmp_path = os.path.join(VOICE_NOTES_DIR, f"tmp_asr_{uuid.uuid4()}.{file_ext}")
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)
        try:
            if hasattr(parser, "parse_file"):
                result = parser.parse_file(tmp_path)  # type: ignore[attr-defined]
            else:
                result = parser.parse(tmp_path)  # type: ignore[arg-type]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    # Normalize output across possible return types
    if isinstance(result, str):
        return result
    try:
        # Document object with page_content
        return getattr(result, "page_content", "")
    except Exception:
        try:
            # List of Documents
            return "\n".join(getattr(doc, "page_content", "") for doc in result)
        except Exception:
            return str(result)

def _title_with_openai(transcribed_text: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    llm = ChatOpenAI(model=OPENAI_TITLE_MODEL, api_key=OPENAI_API_KEY, temperature=0.5)
    resp = llm.invoke(
        f"Generate a short, descriptive title for this transcription:\n\n{transcribed_text}"
    )
    return str(getattr(resp, "content", resp)).strip().replace('"', '')

# Load scenario data
scenarios_path = os.path.join(os.path.dirname(__file__), 'scenarios.json')
with open(scenarios_path, 'r') as f:
    scenarios_data = json.load(f)

def get_scenario_by_id(scenario_id):
    """Finds a scenario in the loaded data by its ID."""
    for scenario in scenarios_data:
        if scenario["id"] == scenario_id:
            return scenario
    return None

def process_interaction(audio_file, current_scenario_id_str):
    """
    Processes the user's audio interaction to determine the next scenario.
    """
    temp_filename = f"temp_{uuid.uuid4()}.webm"
    temp_path = os.path.join(VOICE_NOTES_DIR, temp_filename)

    try:
        current_scenario_id = int(current_scenario_id_str)
        
        # 1. Save temporary audio file to get a stable file path
        audio_bytes = audio_file.read()
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        # 2. Transcribe Audio to Text with provider rotation & fallback
        transcribed_text = None
        try:
            audio_b64 = b64encode(audio_bytes).decode("utf-8")
            message = HumanMessage(
                content=[
                    {"type": "text", "text": "Transcribe this audio recording."},
                    {
                        "type": "file",
                        "source_type": "base64",
                        "mime_type": "audio/webm",
                        "data": audio_b64,
                    },
                ]
            )
            response, key_index = _invoke_google([message])
            transcribed_text = response.content
            usage.log_usage(
                event="interaction_transcribe",
                provider="gemini",
                model=GOOGLE_MODEL,
                key_label=usage.key_label_from_index(key_index, GOOGLE_KEYS),
                status="success",
            )
        except Exception as gerr:
            if _should_google_fallback(gerr):
                # Try OpenAI fallback (webm not natively supported by Whisper unless ffmpeg converts,
                # but often webm/opus works if container is acceptable. If it fails, bubble up.)
                transcribed_text = _transcribe_with_openai(audio_bytes, file_ext="webm")
                usage.log_usage(
                    event="interaction_transcribe",
                    provider="openai",
                    model=OPENAI_TRANSCRIBE_MODEL,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
            else:
                raise gerr

        transcribed_text = (transcribed_text or "").lower()

        # 3. Recognize Intent (Simplified MVP Logic)
        current_scenario = get_scenario_by_id(current_scenario_id)
        if not current_scenario:
            return {"error": "Scenario not found"}

        next_scenario_id = None
        if "yes" in transcribed_text or "yeah" in transcribed_text or "i am" in transcribed_text:
            for option in current_scenario["options"]:
                if "yes" in option["text"].lower():
                    next_scenario_id = option["next_scenario"]
                    break
        elif "no" in transcribed_text or "not" in transcribed_text:
            for option in current_scenario["options"]:
                if "no" in option["text"].lower():
                    next_scenario_id = option["next_scenario"]
                    break
        
        if not next_scenario_id:
            return {"error": f"Could not determine intent from speech. (Heard: '{transcribed_text}')"}

        # 4. Determine Next Scenario
        next_scenario = get_scenario_by_id(next_scenario_id)
        if not next_scenario:
            return {"error": "Next scenario not found"}
            
        return {"nextScenario": next_scenario}

    except Exception as e:
        return {"error": str(e)}
    finally:
        # 5. Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_notes'))
TRANSCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'transcriptions'))

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

        payload = note_store.build_note_payload(base_filename, title_text, transcribed_text)
        note_store.save_note_json(os.path.splitext(base_filename)[0], payload)
        print(f"Successfully saved transcription and title for {base_filename}.")

    except Exception as e:
        print(f"Error during transcription/titling for {wav_path}: {e}")
        if os.path.exists(wav_path):
            payload = note_store.build_note_payload(base_filename, "Title generation failed.", "Transcription failed.")
            note_store.save_note_json(os.path.splitext(base_filename)[0], payload)

def _audio_length_seconds(path: str) -> float | None:
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

def _infer_topics(text: str | None, title: str | None) -> list[str]:
    source = (title or "").strip() or (text or "").strip()
    if not source:
        return []
    # naive keyword extraction: keep alphas, lower, remove stopwords, top 3
    import re

    words = re.findall(r"[A-Za-z]{3,}", source.lower())
    words = [w for w in words if w not in STOPWORDS]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    topics = sorted(freq, key=lambda k: (-freq[k], k))[:3]
    return topics

def get_notes():
    """Lists all notes with their details, including date, topics, and length."""
    notes = []
    if not os.path.exists(VOICE_NOTES_DIR):
        return notes

    # Ensure transcripts dir exists (in case)
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)

    AUDIO_EXTS = ('.wav', '.ogg', '.webm', '.m4a', '.mp3')
    wav_files = [f for f in os.listdir(VOICE_NOTES_DIR) if f.lower().endswith(AUDIO_EXTS)]
    wav_files.sort(key=lambda f: os.path.getmtime(os.path.join(VOICE_NOTES_DIR, f)), reverse=True)
    for filename in wav_files:
        base_filename = filename[:-4]
        audio_path = os.path.join(VOICE_NOTES_DIR, filename)
        data, transcription, title = note_store.load_note_json(base_filename)
        if data is None:
            # JSON not yet created (transcription pending). Return lightweight
            # metadata without creating placeholder JSON to avoid overwriting
            # the final payload when it arrives.
            mtime = os.path.getmtime(audio_path)
            date_str = __import__('datetime').datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            length_sec = note_store.audio_length_seconds(audio_path)
            notes.append({
                "filename": filename,
                "transcription": transcription,  # likely None
                "title": title,  # likely None (frontend will fallback to filename)
                "date": date_str,
                "length_seconds": length_sec,
                "topics": [],
                "tags": [],
            })
            continue
        else:
            data = note_store.ensure_metadata_in_json(base_filename, data)

        notes.append({
            "filename": filename,
            "transcription": transcription,
            "title": title,
            "date": data.get("date"),
            "length_seconds": data.get("length_seconds"),
            "topics": data.get("topics", []),
            "tags": data.get("tags", []),
        })
    return notes
