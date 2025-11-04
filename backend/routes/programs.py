from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request, Response

from core.programs import load_programs_registry, normalize_program_entry, save_programs_registry

router = APIRouter()


@router.get("/api/programs")
async def list_programs():
    return load_programs_registry()


@router.put("/api/programs")
async def replace_programs(request: Request):
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=400, content="Invalid JSON")
    if not isinstance(body, list):
        return Response(status_code=400, content="Body must be a list")
    normalized: List[Dict[str, Any]] = []
    seen: set[str] = set()
    try:
        for item in body:
            if not isinstance(item, dict):
                raise ValueError("Each program must be an object")
            normalized_entry = normalize_program_entry(item)
            key = normalized_entry["key"]
            if key in seen:
                raise ValueError(f"Duplicate program key: {key}")
            seen.add(key)
            normalized.append(normalized_entry)
    except ValueError as exc:
        return Response(status_code=400, content=str(exc))
    save_programs_registry(normalized)
    return {"programs": normalized, "count": len(normalized)}
