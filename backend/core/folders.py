from __future__ import annotations

import json
import os
from typing import List

import config


def _folders_registry_path() -> str:
    os.makedirs(config.FOLDERS_DIR, exist_ok=True)
    return os.path.join(config.FOLDERS_DIR, "folders.json")


def load_folders_registry() -> List[str]:
    try:
        path = _folders_registry_path()
        if not os.path.exists(path):
            return []
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str)]
        return []
    except Exception:
        return []


def save_folders_registry(names: List[str]) -> None:
    path = _folders_registry_path()
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    unique = sorted(list({n.strip(): None for n in names if isinstance(n, str) and n.strip()}.keys()), key=lambda s: s.lower())
    with open(tmp, "w") as f:
        json.dump(unique, f, ensure_ascii=False)
    os.replace(tmp, path)
