import importlib
import pytest


def test_note_store_allows_appwrite(monkeypatch, tmp_path):
    import config as cfg
    import note_store as ns

    voice_dir = tmp_path / "voice_notes"
    trans_dir = tmp_path / "transcriptions"
    voice_dir.mkdir()
    trans_dir.mkdir()

    monkeypatch.setattr(cfg, "STORE_BACKEND", "appwrite", raising=False)
    monkeypatch.setattr(cfg, "VOICE_NOTES_DIR", str(voice_dir), raising=False)
    monkeypatch.setattr(cfg, "TRANSCRIPTS_DIR", str(trans_dir), raising=False)
    monkeypatch.setattr(cfg, "APPWRITE_ENDPOINT", "http://localhost/v1", raising=False)
    monkeypatch.setattr(cfg, "APPWRITE_PROJECT_ID", "test-project", raising=False)
    monkeypatch.setattr(cfg, "APPWRITE_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(cfg, "APPWRITE_DATABASE_ID", "test-db", raising=False)
    monkeypatch.setattr(cfg, "APPWRITE_NOTES_COLLECTION_ID", "test-notes", raising=False)
    importlib.reload(ns)

    (voice_dir / "example.wav").write_bytes(b"")
    ns.save_note_json("example", {"filename": "example.wav", "title": "T", "transcription": "Hello"})
    data, transcription, title = ns.load_note_json("example")
    assert data is not None
    assert transcription == "Hello"
    assert title == "T"


def test_note_store_filesystem_still_functions(monkeypatch, tmp_path):
    import config as cfg
    import note_store as ns

    monkeypatch.setattr(cfg, "STORE_BACKEND", "filesystem", raising=False)
    voice_dir = tmp_path / "voice_notes"
    trans_dir = tmp_path / "transcriptions"
    voice_dir.mkdir()
    trans_dir.mkdir()

    monkeypatch.setattr(cfg, "VOICE_NOTES_DIR", str(voice_dir), raising=False)
    monkeypatch.setattr(cfg, "TRANSCRIPTS_DIR", str(trans_dir), raising=False)
    importlib.reload(ns)

    base = "sample"
    payload = {"filename": "sample.wav", "title": "Test", "transcription": "Hello"}

    (voice_dir / "sample.wav").write_bytes(b"")
    ns.save_note_json(base, payload)
    data, transcription, title = ns.load_note_json(base)

    assert data is not None
    assert transcription == "Hello"
    assert title == "Test"


def test_store_factory_default_filesystem(monkeypatch):
    import config
    from store import get_notes_store
    from store.filesystem import FilesystemNotesStore

    monkeypatch.setattr(config, "STORE_BACKEND", "filesystem", raising=False)
    store = get_notes_store(force_refresh=True)
    assert isinstance(store, FilesystemNotesStore)


def test_store_factory_appwrite_not_ready(monkeypatch):
    import config
    from store import get_notes_store

    monkeypatch.setattr(config, "STORE_BACKEND", "appwrite", raising=False)
    monkeypatch.setattr(config, "APPWRITE_ENDPOINT", "", raising=False)
    monkeypatch.setattr(config, "APPWRITE_PROJECT_ID", "", raising=False)
    monkeypatch.setattr(config, "APPWRITE_API_KEY", "", raising=False)
    with pytest.raises(RuntimeError, match="Appwrite endpoint"):
        get_notes_store(force_refresh=True)
