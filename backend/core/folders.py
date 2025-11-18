from __future__ import annotations

import json
import os
from typing import List, Optional

import config
from store.api import AppwriteClient

_APPWRITE_CLIENT: Optional[AppwriteClient] = None


def _use_appwrite_registry() -> bool:
    return (
        getattr(config, 'STORE_BACKEND', 'filesystem') == 'appwrite'
        and bool(config.APPWRITE_FOLDERS_COLLECTION_ID)
        and bool(config.APPWRITE_DATABASE_ID)
    )


def _get_appwrite_client() -> AppwriteClient:
    global _APPWRITE_CLIENT
    if _APPWRITE_CLIENT is None:
        _APPWRITE_CLIENT = AppwriteClient()
    return _APPWRITE_CLIENT


def _folders_registry_path() -> str:
    os.makedirs(config.FOLDERS_DIR, exist_ok=True)
    return os.path.join(config.FOLDERS_DIR, 'folders.json')


def load_folders_registry() -> List[str]:
    try:
        if _use_appwrite_registry():
            client = _get_appwrite_client()
            collection = config.APPWRITE_FOLDERS_COLLECTION_ID
            cursor = None
            names: List[str] = []
            seen: set[str] = set()
            while True:
                batch = client.list_documents(collection, cursor=cursor, limit=100)
                docs = batch.get('documents', [])
                for doc in docs:
                    name = str((doc.get('data') or doc).get('name') or '').strip()
                    if name and name not in seen:
                        seen.add(name)
                        names.append(name)
                if not docs:
                    break
                cursor = docs[-1]['$id']
            return names
        path = _folders_registry_path()
        if not os.path.exists(path):
            return []
        with open(path, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x).strip() for x in data if isinstance(x, str) and str(x).strip()]
        return []
    except Exception:
        return []


def save_folders_registry(names: List[str]) -> None:
    trimmed = sorted({n.strip() for n in names if isinstance(n, str) and n.strip()}, key=str.lower)
    if _use_appwrite_registry():
        client = _get_appwrite_client()
        collection = config.APPWRITE_FOLDERS_COLLECTION_ID
        existing = client.list_documents(collection, limit=1000)
        existing_ids = {doc['$id'] for doc in existing.get('documents', [])}
        desired = set(trimmed)
        for name in trimmed:
            doc_id = name
            payload = {'name': name}
            try:
                client.update_document(collection, doc_id, payload)
            except Exception:
                client.create_document(collection, doc_id, payload)
        for doc_id in existing_ids - desired:
            try:
                client.delete_document(collection, doc_id)
            except Exception:
                pass
        return
    path = _folders_registry_path()
    tmp = path + '.tmp'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, 'w') as f:
        json.dump(trimmed, f, ensure_ascii=False)
    os.replace(tmp, path)
