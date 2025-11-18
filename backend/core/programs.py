from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import config
from store.api import AppwriteClient


def _programs_registry_path() -> str:
    os.makedirs(config.PROGRAMS_DIR, exist_ok=True)
    return os.path.join(config.PROGRAMS_DIR, "programs.json")


def _use_appwrite_registry() -> bool:
    return (
        getattr(config, "STORE_BACKEND", "filesystem") == "appwrite"
        and bool(config.APPWRITE_PROGRAMS_COLLECTION_ID)
        and bool(config.APPWRITE_DATABASE_ID)
    )


_APPWRITE_CLIENT: Optional[AppwriteClient] = None


def _get_appwrite_client() -> AppwriteClient:
    global _APPWRITE_CLIENT
    if _APPWRITE_CLIENT is None:
        _APPWRITE_CLIENT = AppwriteClient()
    return _APPWRITE_CLIENT


ALLOWED_DOMAINS = {
    "programming",
    "operations",
    "personal",
    "general",
    "research",
    "marketing",
}
DEFAULT_DOMAIN = "general"
KNOWN_FIELDS = {
    "key",
    "title",
    "name",
    "description",
    "domain",
    "keywords",
    "tags",
    "aliases",
    "owners",
    "status",
    "filename_prefix",
    "color",
}


def _normalize_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        parts = [part.strip() for part in value.split(",")]
        return [part for part in parts if part]
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned
    return []


def normalize_program_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    key = str((entry or {}).get("key") or "").strip()
    title = str(
        (entry or {}).get("title")
        or (entry or {}).get("name")
        or ""
    ).strip()
    description = str((entry or {}).get("description") or "").strip()
    raw_domain = str((entry or {}).get("domain") or "").strip().lower()
    domain = raw_domain if raw_domain in ALLOWED_DOMAINS else DEFAULT_DOMAIN
    keywords = _normalize_str_list(entry.get("keywords"))
    tags = _normalize_str_list(entry.get("tags"))
    aliases = _normalize_str_list(entry.get("aliases"))
    owners = _normalize_str_list(entry.get("owners"))
    filename_prefix = str((entry or {}).get("filename_prefix") or "").strip()
    status = str((entry or {}).get("status") or "active").strip()
    color = str((entry or {}).get("color") or "").strip()

    if not key:
        raise ValueError("Program key required")
    if not title:
        title = key.replace("_", " ").title()

    normalized = {
        "key": key,
        "title": title,
        "description": description,
        "domain": domain or DEFAULT_DOMAIN,
        "keywords": keywords,
        "tags": tags,
        "aliases": aliases,
        "owners": owners,
        "status": status or "active",
        "filename_prefix": filename_prefix,
        "color": color,
    }
    for k, v in (entry or {}).items():
        if k in KNOWN_FIELDS:
            continue
        normalized[k] = v
    return normalized


def load_programs_registry() -> List[Dict[str, Any]]:
    try:
        if _use_appwrite_registry():
            client = _get_appwrite_client()
            collection = config.APPWRITE_PROGRAMS_COLLECTION_ID
            cursor = None
            out: List[Dict[str, Any]] = []
            seen: set[str] = set()
            while True:
                batch = client.list_documents(collection, cursor=cursor, limit=100)
                docs = batch.get("documents", [])
                for doc in docs:
                    data = doc.get("data") or doc
                    try:
                        normalized = normalize_program_entry(data)
                    except ValueError:
                        continue
                    if normalized["key"] in seen:
                        continue
                    seen.add(normalized["key"])
                    out.append(normalized)
                if not docs:
                    break
                cursor = docs[-1]["$id"]
            return out
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
    if _use_appwrite_registry():
        client = _get_appwrite_client()
        collection = config.APPWRITE_PROGRAMS_COLLECTION_ID
        # Upsert new programs
        desired_keys = {p["key"] for p in programs}
        try:
            existing_docs = client.list_documents(collection, limit=1000)
            existing_ids = {doc["$id"] for doc in existing_docs.get("documents", [])}
        except Exception:
            existing_ids = set()
        for entry in programs:
            doc_id = entry["key"]
            try:
                client.update_document(collection, doc_id, entry)
            except Exception:
                client.create_document(collection, doc_id, entry)
        # Delete removed programs
        for doc_id in existing_ids - desired_keys:
            try:
                client.delete_document(collection, doc_id)
            except Exception:
                pass
        return
    path = _programs_registry_path()
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(programs, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
