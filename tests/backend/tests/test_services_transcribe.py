import json
import os
import wave


def _write_wav(path: str, seconds: float = 0.1):
    framerate = 8000
    nframes = int(framerate * seconds)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(b"\x00\x00" * nframes)


def test_transcribe_and_save_writes_json(temp_dirs):
    from services import transcribe_and_save
    wav_path = os.path.join(temp_dirs.voice, "sample.wav")
    _write_wav(wav_path)

    import asyncio
    asyncio.run(transcribe_and_save(wav_path))

    json_path = os.path.join(temp_dirs.trans, "sample.json")
    assert os.path.exists(json_path)
    with open(json_path, "r") as f:
        data = json.load(f)
    assert data.get("title")
    assert data.get("transcription")

