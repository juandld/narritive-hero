"""
Provider utilities: Gemini (Google) and OpenAI fallbacks via LangChain.

Encapsulates key rotation, retry strategy decisions, and simple helpers for
transcription and title generation. Keeping this here makes services.py smaller
and easier to scan.
"""

from __future__ import annotations

import io
from typing import List, Optional, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders.parsers.audio import OpenAIWhisperParser

import config


# Initialize Gemini clients (one per API key) for rotation
GOOGLE_KEYS = config.collect_google_api_keys()
GOOGLE_LLMS: List[ChatGoogleGenerativeAI] = [
    ChatGoogleGenerativeAI(model=config.GOOGLE_MODEL, api_key=k) for k in GOOGLE_KEYS
]


def is_rate_limit_error(e: Exception) -> bool:
    s = str(e).lower()
    return (
        "429" in s
        or "rate limit" in s
        or "quota" in s
        or "exceeded your current quota" in s
    )


def should_google_fallback(e: Exception) -> bool:
    s = str(e).lower()
    return is_rate_limit_error(e) or (
        "no google gemini api keys configured" in s
        or "unauthorized" in s
        or "permission" in s
        or "invalid api key" in s
    )


def key_label_from_index(index: int) -> str:
    try:
        key = GOOGLE_KEYS[index]
    except Exception:
        return f"gemini_key_{index}"
    return f"gemini_key_{index}_{key[-4:] if key else '????'}"


def invoke_google(messages: List[HumanMessage]) -> Tuple[object, int]:
    """Try Gemini clients in order (no internal retries). Returns (response, key_index)."""
    last_err: Optional[Exception] = None
    for idx, llm in enumerate(GOOGLE_LLMS):
        try:
            # Disable internal retries by overriding keyword
            return llm.invoke(messages, max_retries=0), idx
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    raise RuntimeError("No Google Gemini API keys configured.")


def title_with_openai(text: str) -> str:
    """Generate a short title via OpenAI (LangChain)."""
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    llm = ChatOpenAI(model=config.OPENAI_TITLE_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.5)
    resp = llm.invoke(
        f"Generate a short, descriptive title for this transcription:\n\n{text}"
    )
    return str(getattr(resp, "content", resp)).strip().replace('"', '')


def transcribe_with_openai(audio_bytes: bytes, file_ext: str = "wav") -> str:
    """Transcribe audio using LangChain OpenAI Whisper parser.

    Falls back to writing a temp file if direct bytes are not supported.
    """
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    parser = OpenAIWhisperParser(api_key=config.OPENAI_API_KEY, model=config.OPENAI_TRANSCRIBE_MODEL)
    try:
        # Some parser versions support bytes directly
        result = parser.parse(audio_bytes)  # type: ignore[arg-type]
    except Exception:
        # Use in-memory file-like object if needed
        bio = io.BytesIO(audio_bytes)
        bio.name = f"audio.{file_ext}"
        result = parser.parse(bio)  # type: ignore[arg-type]
    if isinstance(result, str):
        return result
    return getattr(result, "page_content", str(result))

