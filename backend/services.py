import os
import json
import uuid
import io
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.document_loaders.parsers.audio import OpenAIWhisperParser
from base64 import b64encode
from typing import List, Optional, Tuple
import usage_log as usage

# Load environment variables from .env file
load_dotenv()

# Configure providers and models
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
OPENAI_TITLE_MODEL = os.getenv("OPENAI_TITLE_MODEL", "gpt-4o-mini")

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

async def transcribe_and_save(wav_path):
    """Transcribes and titles an audio file, saving the results."""
    base_filename = os.path.basename(wav_path)
    print(f"Starting transcription process for {base_filename}...")
    try:
        # Read audio bytes
        with open(wav_path, "rb") as af:
            audio_bytes = af.read()

        # Transcribe with provider rotation & fallback
        print(f"Transcribing {base_filename} from local file bytes...")
        try:
            audio_b64 = b64encode(audio_bytes).decode("utf-8")
            transcription_message = HumanMessage(
                content=[
                    {"type": "text", "text": "Transcribe this audio recording."},
                    {
                        "type": "file",
                        "source_type": "base64",
                        "mime_type": "audio/wav",
                        "data": audio_b64,
                    },
                ]
            )
            # Use sync path without internal async retries; run in a thread
            transcription_response, key_index = await asyncio.to_thread(
                _invoke_google, [transcription_message]
            )
            transcribed_text = transcription_response.content
            usage.log_usage(
                event="transcribe",
                provider="gemini",
                model=GOOGLE_MODEL,
                key_label=usage.key_label_from_index(key_index, GOOGLE_KEYS),
                status="success",
            )
        except Exception as gerr:
            if _should_google_fallback(gerr):
                # Fallback to OpenAI Whisper
                transcribed_text = _transcribe_with_openai(audio_bytes, file_ext="wav")
                usage.log_usage(
                    event="transcribe",
                    provider="openai",
                    model=OPENAI_TRANSCRIBE_MODEL,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
            else:
                raise gerr
        print(f"Successfully transcribed {base_filename}.")

        # Generate title
        print(f"Generating title for {base_filename}...")
        try:
            title_message = HumanMessage(
                content=[
                    {"type": "text", "text": f"Generate a short, descriptive title for this transcription:\n\n{transcribed_text}"},
                ]
            )
            # Use sync path without internal async retries; run in a thread
            title_response, key_index = await asyncio.to_thread(
                _invoke_google, [title_message]
            )
            title_text = title_response.content.strip().replace('"', '')
            usage.log_usage(
                event="title",
                provider="gemini",
                model=GOOGLE_MODEL,
                key_label=usage.key_label_from_index(key_index, GOOGLE_KEYS),
                status="success",
            )
        except Exception as gerr:
            if _should_google_fallback(gerr):
                title_text = _title_with_openai(transcribed_text)
                usage.log_usage(
                    event="title",
                    provider="openai",
                    model=OPENAI_TITLE_MODEL,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
            else:
                raise gerr
        print(f"Successfully generated title for {base_filename}.")

        # Save transcription and title
        txt_filename = base_filename.replace('.wav', '.txt')
        title_filename = base_filename.replace('.wav', '.title')

        with open(os.path.join(VOICE_NOTES_DIR, txt_filename), 'w') as f:
            f.write(transcribed_text)
        with open(os.path.join(VOICE_NOTES_DIR, title_filename), 'w') as f:
            f.write(title_text)
        print(f"Successfully saved transcription and title for {base_filename}.")

    except Exception as e:
        print(f"Error during transcription/titling for {wav_path}: {e}")
        # Save error messages to files to prevent re-processing
        txt_filename = base_filename.replace('.wav', '.txt')
        title_filename = base_filename.replace('.wav', '.title')
        with open(os.path.join(VOICE_NOTES_DIR, txt_filename), 'w') as f:
            f.write("Transcription failed.")
        with open(os.path.join(VOICE_NOTES_DIR, title_filename), 'w') as f:
            f.write("Title generation failed.")

def get_notes():
    """Lists all notes with their details."""
    notes = []
    if not os.path.exists(VOICE_NOTES_DIR):
        return notes

    # Sort by modification time, newest first, so fresh uploads are visible at top
    wav_files = [f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.wav')]
    wav_files.sort(key=lambda f: os.path.getmtime(os.path.join(VOICE_NOTES_DIR, f)), reverse=True)
    for filename in wav_files:
        base_filename = filename.replace('.wav', '')
        txt_path = os.path.join(VOICE_NOTES_DIR, f"{base_filename}.txt")
        title_path = os.path.join(VOICE_NOTES_DIR, f"{base_filename}.title")

        transcription = None
        if os.path.exists(txt_path):
            with open(txt_path, 'r') as f:
                transcription = f.read()

        title = None
        if os.path.exists(title_path):
            with open(title_path, 'r') as f:
                title = f.read()

        notes.append({
            "filename": filename,
            "transcription": transcription,
            "title": title,
        })
    return notes
