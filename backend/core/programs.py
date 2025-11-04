from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import config


def _programs_registry_path() -> str:
    os.makedirs(config.PROGRAMS_DIR, exist_ok=True)
    return os.path.join(config.PROGRAMS_DIR, "programs.json")


def normalize_program_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    key = str((entry or {}).get("key") or "").strip()
    title = str((entry or {}).get("title") or "").strip()
    description = str((entry or {}).get("description") or "").strip()
    domain = str((entry or {}).get("domain") or "").strip() or "general"
    raw_keywords = entry.get("keywords") or []

    keywords: List[str] = []
    if isinstance(raw_keywords, str):
        raw_keywords = [part.strip() for part in raw_keywords.split(",") if part.strip()]
    if isinstance(raw_keywords, list):
        keywords = [str(k).strip() for k in raw_keywords if str(k).strip()]

    if not key:
        raise ValueError("Program key required")
    if not title:
        title = key.replace("_", " ").title()

    return {
        "key": key,
        "title": title,
        "description": description,
        "domain": domain,
        "keywords": keywords,
    }


def load_programs_registry() -> List[Dict[str, Any]]:
    try:
        path = _programs_registry_path()
        if not os.path.exists(path):
            return []
        with open(path, "r") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        out: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for raw in data:
            if not isinstance(raw, dict):
                continue
            try:
                normalized = normalize_program_entry(raw)
            except ValueError:
                continue
            if normalized["key"] in seen:
                continue
            seen.add(normalized["key"])
            out.append(normalized)
        return out
    except Exception:
        return []


def save_programs_registry(programs: List[Dict[str, Any]]) -> None:
    path = _programs_registry_path()
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(programs, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
