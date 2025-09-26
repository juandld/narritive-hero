import json
import os
from fastapi.testclient import TestClient


def test_get_notes_empty(temp_dirs):
    from main import app
    client = TestClient(app)
    r = client.get("/api/notes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert r.json() == []


def test_generate_narrative_with_extra_text(temp_dirs):
    base = "testfile"
    jpath = os.path.join(temp_dirs.trans, f"{base}.json")
    with open(jpath, "w") as f:
        json.dump({"title": "T1", "transcription": "Hello world"}, f)

    from main import app
    client = TestClient(app)

    payload = {
        "items": [{"filename": f"{base}.wav"}],
        "extra_text": "Some context",
        "provider": "openai",
    }
    r = client.post("/api/narratives/generate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data and data["filename"].endswith(".txt")

    out_path = os.path.join(temp_dirs.narr, data["filename"])
    assert os.path.exists(out_path)
    with open(out_path, "r") as f:
        content = f.read()
    assert "Generated Narrative" in content or content.strip()

