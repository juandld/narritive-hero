import os
import json
import sys
import types


def setup_temp_dirs():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".tmp", str(os.getpid())))
    voice = os.path.join(base, "voice_notes")
    trans = os.path.join(base, "transcriptions")
    narr = os.path.join(base, "narratives")
    programs = os.path.join(base, "programs")
    os.makedirs(voice, exist_ok=True)
    os.makedirs(trans, exist_ok=True)
    os.makedirs(narr, exist_ok=True)
    os.makedirs(programs, exist_ok=True)
    return types.SimpleNamespace(base=base, voice=voice, trans=trans, narr=narr, programs=programs)


def install_stubs():
    # Stub providers module to avoid importing external SDKs
    providers = types.ModuleType("providers")

    class Dummy:
        def __init__(self, content="OK"):
            self.content = content

    def invoke_google(msgs, model=None):
        return Dummy("OK"), 0

    def transcribe_with_openai(b, file_ext="wav"):
        return "OK_TRANSCRIPT"

    def title_with_openai(text):
        return "OK Title"

    def openai_chat(messages, model=None, temperature=0.2):
        return "Generated Narrative"

    def key_label_from_index(index: int):
        return f"gemini_key_{index}_stub"

    def normalize_title_output(raw: str) -> str:
        return (raw or "").strip() or "Untitled"

    providers.invoke_google = invoke_google
    providers.transcribe_with_openai = transcribe_with_openai
    providers.title_with_openai = title_with_openai
    providers.openai_chat = openai_chat
    providers.key_label_from_index = key_label_from_index
    providers.normalize_title_output = normalize_title_output

    sys.modules["providers"] = providers

    # Stub langchain_core.messages.HumanMessage
    lc_messages = types.ModuleType("langchain_core.messages")

    class HumanMessage:
        def __init__(self, content):
            self.content = content

    lc_messages.HumanMessage = HumanMessage
    # Ensure the package namespace exists
    sys.modules["langchain_core"] = types.ModuleType("langchain_core")
    sys.modules["langchain_core.messages"] = lc_messages

    # Stub dotenv.load_dotenv
    dotenv = types.ModuleType("dotenv")
    def load_dotenv(*args, **kwargs):
        return None
    dotenv.load_dotenv = load_dotenv
    sys.modules["dotenv"] = dotenv


def patch_paths(tmp):
    import importlib
    config = importlib.import_module("config")
    services = importlib.import_module("services")
    utils = importlib.import_module("utils")
    try:
        main = importlib.import_module("main")
    except Exception:
        main = None

    for mod, attr, val in [
        (config, "VOICE_NOTES_DIR", tmp.voice),
        (config, "TRANSCRIPTS_DIR", tmp.trans),
        (config, "PROGRAMS_DIR", tmp.programs),
        (services, "VOICE_NOTES_DIR", tmp.voice),
        (services, "TRANSCRIPTS_DIR", tmp.trans),
        (utils, "VOICE_NOTES_DIR", tmp.voice),
        (utils, "TRANSCRIPTS_DIR", tmp.trans),
    ]:
        setattr(mod, attr, val)
    if main is not None:
        for attr, val in (
            ("VOICE_NOTES_DIR", tmp.voice),
            ("TRANSCRIPTS_DIR", tmp.trans),
            ("NARRATIVES_DIR", tmp.narr),
            ("PROGRAMS_DIR", tmp.programs),
        ):
            setattr(main, attr, val)


def test_get_notes_empty():
    from main import app
    try:
        from fastapi.testclient import TestClient
    except Exception:
        print("SKIP: TestClient not available")
        return True
    client = TestClient(app)
    r = client.get("/api/notes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert r.json() == []
    return True


def test_generate_narrative(tmp):
    # Create source json
    with open(os.path.join(tmp.trans, "src.json"), "w") as f:
        json.dump({"title": "T1", "transcription": "Hello"}, f)
    from main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    payload = {"items": [{"filename": "src.wav"}], "extra_text": "ctx", "provider": "openai"}
    r = client.post("/api/narratives/generate", json=payload)
    assert r.status_code == 200
    fn = r.json()["filename"]
    assert fn.endswith(".txt")
    assert os.path.exists(os.path.join(tmp.narr, fn))
    return True


def test_transcribe_and_save(tmp):
    # Create a tiny wav
    import wave
    wav_path = os.path.join(tmp.voice, "s.wav")
    with wave.open(wav_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x00" * 800)
    import asyncio
    from services import transcribe_and_save
    asyncio.run(transcribe_and_save(wav_path))
    assert os.path.exists(os.path.join(tmp.trans, "s.json"))
    return True


def main():
    tmp = setup_temp_dirs()
    install_stubs()
    patch_paths(tmp)
    tests = []
    # Include API tests only if FastAPI is available
    try:
        import fastapi  # noqa: F401
        tests.extend([
            ("GET /api/notes empty", test_get_notes_empty),
            ("POST /api/narratives/generate", lambda: test_generate_narrative(tmp)),
        ])
    except Exception:
        print("NOTE: FastAPI not available; skipping API smoke tests.")
    tests.append(("services.transcribe_and_save", lambda: test_transcribe_and_save(tmp)))
    failures = 0
    total = len(tests)
    print("\n=== Narrative Hero Smoke Tests ===")
    for name, fn in tests:
        try:
            fn()
            print(f"✓ {name}")
        except Exception as e:
            failures += 1
            print(f"✗ {name}: {e}")
    print(f"\nSummary: {total - failures}/{total} passed")
    import shutil
    shutil.rmtree(tmp.base, ignore_errors=True)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
