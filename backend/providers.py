"""
Provider utilities: Gemini (Google) and OpenAI fallbacks via LangChain.

This module is designed to be light to import for tests and app startup.
To avoid slow imports and side effects, heavyweight SDKs and client objects
are created lazily inside function bodies rather than at module import time.
"""

from __future__ import annotations

import io
from typing import List, Optional, Tuple, Dict

import logging
from langchain_core.messages import HumanMessage

import config

# Initialize module logger early (before any usage)
logger = logging.getLogger("narrative.providers")


# Collect Gemini API keys (cheap and side‑effect free)
GOOGLE_KEYS = config.collect_google_api_keys()

# Lazy cache for constructed Gemini clients keyed by model
_GOOGLE_LLMS_CACHE: Dict[str, List[object]] = {}

def _get_google_llms(model: Optional[str] = None) -> List[object]:
    """Build or fetch cached Gemini clients for the given model lazily.

    Import of langchain/SDKs happens inside to keep module import fast.
    """
    use_model = model or config.GOOGLE_MODEL
    if use_model in _GOOGLE_LLMS_CACHE:
        return _GOOGLE_LLMS_CACHE[use_model]
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI  # local import
    except Exception as e:
        raise RuntimeError("Gemini provider not available: langchain_google_genai missing") from e
    llms = [ChatGoogleGenerativeAI(model=use_model, api_key=k) for k in GOOGLE_KEYS]
    _GOOGLE_LLMS_CACHE[use_model] = llms
    logger.info("Gemini configured: model=%s, keys=%s", use_model, len(GOOGLE_KEYS))
    return llms


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
        or "not found" in s
        or "publisher model" in s
    )


def key_label_from_index(index: int) -> str:
    try:
        key = GOOGLE_KEYS[index]
    except Exception:
        return f"gemini_key_{index}"
    return f"gemini_key_{index}_{key[-4:] if key else '????'}"


def invoke_google(messages: List[HumanMessage], model: Optional[str] = None) -> Tuple[object, int]:
    """Try Gemini clients in order (no internal retries). Returns (response, key_index).

    If `model` is provided, use a transient set of clients for that model.
    """
    last_err: Optional[Exception] = None
    # Build or fetch LLM rotation lazily
    llms = _get_google_llms(model)
    for idx, llm in enumerate(llms):
        try:
            # Disable internal retries by overriding keyword
            return llm.invoke(messages, max_retries=0), idx
        except Exception as e:
            last_err = e
            logger.warning(
                "Gemini invoke failed on key_index=%s: %s", idx, str(e)
            )
            continue
    if last_err:
        raise last_err
    raise RuntimeError("No Google Gemini API keys configured.")


def title_with_openai(text: str) -> str:
    """Generate a short title via OpenAI (LangChain)."""
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    from langchain_openai import ChatOpenAI  # local import
    llm = ChatOpenAI(model=config.OPENAI_TITLE_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.3)
    prompt = (
        "Return exactly one short title (5–8 words) for the transcription below. "
        "Use the same language as the transcription. Do not include quotes, bullets, markdown, or any extra text. "
        "Output only the title on a single line.\n\n" + text
    )
    resp = llm.invoke(prompt)
    raw = str(getattr(resp, "content", resp))
    return normalize_title_output(raw)


def openai_chat(messages: List[HumanMessage], model: Optional[str] = None, temperature: float = 0.2) -> str:
    """Generic OpenAI chat wrapper returning content text."""
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    from langchain_openai import ChatOpenAI  # local import
    use_model = model or config.OPENAI_NARRATIVE_MODEL
    llm = ChatOpenAI(model=use_model, api_key=config.OPENAI_API_KEY, temperature=temperature)
    resp = llm.invoke(messages)
    return str(getattr(resp, "content", resp))


def normalize_title_output(raw: str) -> str:
    """Coerce LLM output into a single, clean title line.

    - Removes markdown (bullets, bold/italics) and boilerplate prefaces
    - Picks the first plausible title line
    - Trims excessive punctuation and length
    """
    try:
        text = (raw or "").strip()
        if not text:
            return "Untitled"
        # Remove obvious prefaces
        lower = text.lower()
        if "here are" in lower and ":" in text:
            # Cut off everything up to and including the first colon
            text = text.split(":", 1)[-1].strip()
        # Split lines and scan for first candidate
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        candidates = []
        for line in lines:
            # Skip section headings that end with a colon
            if line.endswith(":"):
                continue
            # Remove common list markers
            l = line
            for prefix in ("- ", "* ", "• ", "1. ", "2. ", "3. ", "-", "*", "•"):
                if l.startswith(prefix):
                    l = l[len(prefix):].strip()
            # Strip markdown bold/italics markers
            l = l.replace("**", "").replace("__", "").replace("*", "").replace("_", "").strip()
            if l:
                candidates.append(l)
        if not candidates:
            candidates = [text]
        title = candidates[0]
        # If still contains multiple suggestions separated by bullets or semicolons, take first chunk
        for sep in [" • ", " | ", ";", "  -  ", "  *  "]:
            if sep in title:
                title = title.split(sep, 1)[0].strip()
        # Trim quotes and trailing punctuation
        title = title.strip().strip('"').strip("'")
        while title and title[-1] in [".", ":", "-", "|", ";"]:
            title = title[:-1].rstrip()
        # Limit length sensibly without cutting words mid-way
        if len(title) > 80:
            parts = title.split()
            out = []
            for p in parts:
                if len(" ".join(out + [p])) <= 80:
                    out.append(p)
                else:
                    break
            if out:
                title = " ".join(out)
        return title or "Untitled"
    except Exception:
        return "Untitled"


def transcribe_with_openai(audio_bytes: bytes, file_ext: str = "wav") -> str:
    """Transcribe audio using OpenAI Whisper via the official SDK.

    This avoids version mismatches in LangChain parsers and works reliably with bytes.
    """
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    bio = io.BytesIO(audio_bytes)
    bio.name = f"audio.{file_ext}"
    resp = client.audio.transcriptions.create(
        model=config.OPENAI_TRANSCRIBE_MODEL,
        file=bio,
        response_format="text",
    )
    return resp if isinstance(resp, str) else getattr(resp, "text", "")
