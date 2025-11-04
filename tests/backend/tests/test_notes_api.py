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


def test_telegram_text_flow_returns_feedback(monkeypatch, temp_dirs):
    from main import app
    client = TestClient(app)

    client.put(
        "/api/programs",
        json=[
            {"key": "ops", "title": "Operations", "domain": "operations", "keywords": ["vendor", "follow", "meeting"]},
            {"key": "ai_pipeline", "title": "AI", "domain": "programming", "keywords": ["fastapi"]},
        ],
    )

    payload = {
        "message": "Follow up with Alex about vendor shortlist.",
        "folder": "Operations",
        "tags": ["urgent", "follow-up"],
    }
    resp = client.post("/api/integrations/telegram", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "telegram"
    assert data["input_type"] == "text"
    assert data["folder"] == "Operations"
    assert "urgent" in data["tags"]
    assert data["summary"] == "OK"
    assert data["feedback"].startswith("Snapshot:")
    assert data["status"].startswith("Saved “")
    assert data["auto_category"] == "operations"
    assert data["auto_program"] == "ops"


def test_telegram_audio_flow_with_stubbed_create_note(monkeypatch, temp_dirs):
    from main import app

    async def fake_process_audio_upload(file, background_tasks, date=None, place=None, folder=None):
        assert folder == "Ideas"
        filename = "voice-note.m4a"
        base = os.path.splitext(filename)[0]
        json_path = os.path.join(temp_dirs.trans, f"{base}.json")
        with open(json_path, "w") as f:
            json.dump(
                {
                    "filename": filename,
                    "title": "Voice Idea",
                    "transcription": "We need to refactor the FastAPI embedding service soon.",
                    "folder": folder or "",
                    "tags": [{"label": "telegram"}],
                    "created_at": "2024-11-02T00:00:00",
                    "created_ts": 1730505600000,
                },
                f,
            )
        return {"filename": filename, "message": "stubbed upload"}

    monkeypatch.setattr("core.note_logic.process_audio_upload", fake_process_audio_upload)

    client = TestClient(app)
    client.put(
        "/api/programs",
        json=[
            {"key": "ai_pipeline", "title": "AI Pipeline", "domain": "programming", "keywords": ["fastapi", "embedding", "service"]},
        ],
    )
    files = {"file": ("note.m4a", b"fake-bytes", "audio/m4a")}
    data = {"folder": "Ideas", "tags": "voice"}

    resp = client.post("/api/integrations/telegram", files=files, data=data)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["source"] == "telegram"
    assert payload["input_type"] == "audio"
    assert payload["folder"] == "Ideas"
    assert "voice" in payload["tags"]
    assert payload["transcription_status"] == "complete"
    assert payload["summary"] == "OK"
    assert payload["feedback"].startswith("Snapshot: OK")
    assert payload["auto_category"] == "programming"
    assert payload["auto_program"] == "ai_pipeline"


def test_text_note_creation_includes_auto_category(temp_dirs):
    from main import app
    client = TestClient(app)

    programs_payload = [
        {"key": "ai_pipeline", "title": "AI Pipeline", "domain": "programming", "keywords": ["embedding", "fastapi"]},
    ]
    put_res = client.put("/api/programs", json=programs_payload)
    assert put_res.status_code == 200

    note_payload = {
        "transcription": "We need to refactor the FastAPI embedding service.",
        "title": "Embedding refactor",
    }
    res = client.post("/api/notes/text", json=note_payload)
    assert res.status_code == 200
    data = res.json()
    assert data.get("auto_category") == "programming"
    assert data.get("auto_program") == "ai_pipeline"
    assert data.get("auto_program_confidence") is not None

    # Ensure JSON on disk mirrors classification
    stored_json = os.listdir(temp_dirs.trans)
    assert stored_json, "note json not created"
    path = os.path.join(temp_dirs.trans, stored_json[0])
    with open(path, "r") as fh:
        stored = json.load(fh)
    assert stored.get("auto_category") == "programming"
    assert stored.get("auto_program") == "ai_pipeline"
