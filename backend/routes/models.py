from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from fastapi import APIRouter

import config

router = APIRouter()
logger = logging.getLogger(__name__)

_MODELS_CACHE: Dict[str, tuple[float, List[str]]] = {}


def _cache_set(key: str, values: List[str], ttl: float = 600.0) -> List[str]:
    _MODELS_CACHE[key] = (time.time() + ttl, values)
    return values


def _cache_get(key: str) -> Optional[List[str]]:
    exp_vals = _MODELS_CACHE.get(key)
    if not exp_vals:
        return None
    exp, vals = exp_vals
    if time.time() > exp:
        _MODELS_CACHE.pop(key, None)
        return None
    return vals


def _list_openai_latest() -> List[str]:
    cached = _cache_get("openai")
    if cached is not None:
        return cached
    ids: List[str] = []
    try:
        from openai import OpenAI

        if not getattr(config, "OPENAI_API_KEY", None):
            raise RuntimeError("no openai key")
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.models.list()
        all_ids = [
            getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else None)
            for m in getattr(resp, "data", [])
        ]
        all_ids = [str(x) for x in all_ids if x]
        prefer_pro = ["gpt-4.1", "gpt-4o"]
        prefer_mini = ["gpt-4.1-mini", "gpt-4o-mini"]
        lower_set = {str(x).lower() for x in all_ids}
        picks: List[str] = []
        for p in prefer_pro:
            if p.lower() in lower_set:
                picks.append(p)
                break
        for p in prefer_mini:
            if p.lower() in lower_set:
                if not picks or picks[-1].lower() != p.lower():
                    picks.append(p)
                break
        if not picks:
            picks = [getattr(config, "OPENAI_NARRATIVE_MODEL", "gpt-4o"), "gpt-4.1-mini"]
        ids = picks
    except Exception:
        ids = [getattr(config, "OPENAI_NARRATIVE_MODEL", "gpt-4o"), "gpt-4.1-mini"]
    seen: set[str] = set()
    out: List[str] = []
    for x in ids:
        xl = str(x).strip()
        if xl and xl.lower() not in seen:
            seen.add(xl.lower())
            out.append(xl)
    return _cache_set("openai", out)


def _list_gemini_latest() -> List[str]:
    cached = _cache_get("gemini")
    if cached is not None:
        return cached
    ids: List[str] = []
    try:
        import google.generativeai as genai  # type: ignore

        keys = config.collect_google_api_keys()
        if not keys:
            raise RuntimeError("No Google Gemini keys configured")
        genai.configure(api_key=keys[0])
        models = genai.list_models()
        avail: set[str] = set()
        for m in models:
            mid = getattr(m, "name", "") or getattr(m, "model", "") or ""
            s = str(mid).split("/")[-1].lower()
            if s.startswith("gemini-"):
                avail.add(s)
        prefer_pro = ["gemini-2.5-pro-latest", "gemini-2.5-pro", "gemini-2-pro", "gemini-2-latest"]
        prefer_flash = ["gemini-2.5-flash-latest", "gemini-2.5-flash", "gemini-2-flash", "gemini-2-latest"]
        picks: List[str] = []
        for p in prefer_pro:
            if p in avail:
                picks.append(p)
                break
        for p in prefer_flash:
            if p in avail:
                if not picks or picks[-1] != p:
                    picks.append(p)
                break
        if not picks:
            picks = [getattr(config, "GOOGLE_MODEL", "gemini-2.5-flash"), "gemini-2.5-pro"]
        ids = picks
    except Exception as e:
        logger.debug("Gemini model listing failed: %s", e)
        ids = [getattr(config, "GOOGLE_MODEL", "gemini-2.5-flash"), "gemini-2.5-pro"]

    def sort_key(x: str):
        xl = x.lower()
        latest = xl.endswith("-latest")
        pro = "-pro" in xl
        import re

        m = re.search(r"gemini-(\d+(?:\.\d+)?)", xl)
        ver = float(m.group(1)) if m else 0.0
        return (0 if latest else 1, -ver, 0 if pro else 1, xl)

    seen: set[str] = set()
    out: List[str] = []
    for it in sorted(ids, key=sort_key):
        if it not in seen:
            seen.add(it)
            out.append(it)
        if len(out) >= 2:
            break
    return _cache_set("gemini", out or [getattr(config, "GOOGLE_MODEL", "gemini-2.5-flash")])


@router.get("/api/models")
async def list_models(provider: str = "auto", q: str = ""):
    prov = (provider or "auto").lower()
    query = (q or "").strip().lower()
    if prov == "gemini":
        models = _list_gemini_latest()
    elif prov == "openai":
        models = _list_openai_latest()
    else:
        models = _list_gemini_latest() + _list_openai_latest()
    if query:
        models = [m for m in models if query in m.lower()]
    return {"models": models}
