import json
import os
from fastapi.testclient import TestClient


def test_programs_get_empty(temp_dirs):
    from main import app
    client = TestClient(app)
    res = client.get("/api/programs")
    assert res.status_code == 200
    assert res.json() == []


def test_programs_put_and_roundtrip(temp_dirs):
    from main import app
    client = TestClient(app)
    payload = [
        {"key": "ai_pipeline", "title": "AI Pipeline", "description": "Vector + inference work", "domain": "programming", "keywords": ["vector", "embedding", "api"]},
        {"key": "operations", "title": "Operations", "description": "Ops improvements", "keywords": ["ops", "process"]},
    ]
    res = client.put("/api/programs", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 2
    stored = body["programs"]
    assert stored[0]["key"] == "ai_pipeline"
    assert stored[0]["domain"] == "programming"
    assert stored[0]["keywords"] == ["vector", "embedding", "api"]
    # Ensure persisted
    path = os.path.join(temp_dirs.programs, "programs.json")
    with open(path, "r") as fh:
        on_disk = json.load(fh)
    assert isinstance(on_disk, list) and len(on_disk) == 2
    res2 = client.get("/api/programs")
    assert res2.status_code == 200
    assert len(res2.json()) == 2
