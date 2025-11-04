import os
import sys
import shutil
import types
import pytest


# Ensure the backend package is importable
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@pytest.fixture()
def temp_dirs(monkeypatch):
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".pytest_tmp", str(os.getpid())))
    voice = os.path.join(base, "voice_notes")
    trans = os.path.join(base, "transcriptions")
    narr = os.path.join(base, "narratives")
    programs = os.path.join(base, "programs")
    os.makedirs(voice, exist_ok=True)
    os.makedirs(trans, exist_ok=True)
    os.makedirs(narr, exist_ok=True)
    os.makedirs(programs, exist_ok=True)

    # Patch paths inside modules
    import importlib
    config = importlib.import_module("config")
    main = importlib.import_module("main")
    services = importlib.import_module("services")
    utils = importlib.import_module("utils")
    routes_narratives = importlib.import_module("routes.narratives")

    monkeypatch.setattr(config, "VOICE_NOTES_DIR", voice, raising=False)
    monkeypatch.setattr(config, "TRANSCRIPTS_DIR", trans, raising=False)
    monkeypatch.setattr(config, "PROGRAMS_DIR", programs, raising=False)
    monkeypatch.setattr(config, "NARRATIVES_DIR", narr, raising=False)
    monkeypatch.setattr(main, "VOICE_NOTES_DIR", voice, raising=False)
    monkeypatch.setattr(main, "TRANSCRIPTS_DIR", trans, raising=False)
    monkeypatch.setattr(main, "NARRATIVES_DIR", narr, raising=False)
    monkeypatch.setattr(main, "PROGRAMS_DIR", programs, raising=False)
    monkeypatch.setattr(services, "VOICE_NOTES_DIR", voice, raising=False)
    monkeypatch.setattr(services, "TRANSCRIPTS_DIR", trans, raising=False)
    monkeypatch.setattr(utils, "VOICE_NOTES_DIR", voice, raising=False)
    monkeypatch.setattr(utils, "TRANSCRIPTS_DIR", trans, raising=False)
    monkeypatch.setattr(routes_narratives, "NARRATIVES_DIR", narr, raising=False)
    monkeypatch.setattr(routes_narratives, "NARRATIVE_META_DIR", os.path.join(narr, "meta"), raising=False)
    monkeypatch.setattr(routes_narratives, "TRANSCRIPTS_DIR", trans, raising=False)

    yield types.SimpleNamespace(base=base, voice=voice, trans=trans, narr=narr, programs=programs)

    shutil.rmtree(base, ignore_errors=True)


@pytest.fixture(autouse=True)
def stub_providers(monkeypatch):
    import providers

    class Dummy:
        def __init__(self, content="OK"):
            self.content = content

    monkeypatch.setattr(providers, "invoke_google", lambda msgs, model=None: (Dummy("OK"), 0))
    monkeypatch.setattr(providers, "transcribe_with_openai", lambda b, file_ext="wav": "OK_TRANSCRIPT")
    monkeypatch.setattr(providers, "title_with_openai", lambda text: "OK Title")
    monkeypatch.setattr(providers, "openai_chat", lambda messages, model=None, temperature=0.2: "Generated Narrative")

    yield
