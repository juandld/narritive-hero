import os
import json
import shutil
import asyncio
import wave
import contextlib
from datetime import datetime
from services import transcribe_and_save
import usage_log as usage
import config

# Centralized paths; keep module vars for monkeypatching in tests
APP_DIR = config.BASE_DIR
VOICE_NOTES_DIR = config.VOICE_NOTES_DIR
TRANSCRIPTS_DIR = config.TRANSCRIPTS_DIR

async def on_startup():
    """On startup, create voice notes dir and backfill any missing transcriptions."""
    if not os.path.exists(VOICE_NOTES_DIR):
        os.makedirs(VOICE_NOTES_DIR)
    if not os.path.exists(TRANSCRIPTS_DIR):
        os.makedirs(TRANSCRIPTS_DIR)
    # Ensure narratives dir exists under storage
    try:
        import config as _cfg
        NARRATIVES_DIR = getattr(_cfg, "NARRATIVES_DIR", os.path.join(APP_DIR, "storage", "narratives"))
    except Exception:
        NARRATIVES_DIR = os.path.join(APP_DIR, "storage", "narratives")
    if not os.path.exists(NARRATIVES_DIR):
        os.makedirs(NARRATIVES_DIR)
    # Ensure formats dir exists
    try:
        from config import FORMATS_DIR as _FORMATS_DIR
        os.makedirs(_FORMATS_DIR, exist_ok=True)
    except Exception:
        pass
    # titles directory is deprecated; we will migrate any leftover files below
    # Ensure usage logging directory/files exist
    usage.ensure_usage_paths()
    
    print("Checking for missing transcriptions...")
    # Legacy consolidation disabled: only JSON is considered

    AUDIO_EXTS = ('.wav', '.ogg', '.webm', '.m4a', '.mp3')
    wav_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.lower().endswith(AUDIO_EXTS)}
    json_files = {f for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.json')}
    # Ignore any legacy .txt/.title files

    tasks = []
    for wav_file in wav_files:
        base = os.path.splitext(wav_file)[0]
        json_filename = base + '.json'
        # If JSON missing, schedule transcription/title generation
        if json_filename not in json_files:
            wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
            tasks.append(transcribe_and_save(wav_path))
        else:
            # JSON exists. Re-transcribe only if it previously failed.
            json_path = os.path.join(TRANSCRIPTS_DIR, json_filename)
            try:
                with open(json_path, 'r') as jf:
                    data = json.load(jf)
                if data.get('transcription') == 'Transcription failed.':
                    wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                    tasks.append(transcribe_and_save(wav_path))
                else:
                    continue
            except Exception:
                # If unreadable, try to regenerate
                wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                tasks.append(transcribe_and_save(wav_path))

    # Ensure metadata fields (language/topics/tags/folder/length/date) exist on all JSONs
    try:
        import note_store as _ns
        count_updated = 0
        for fn in list(os.listdir(TRANSCRIPTS_DIR)):
            if not fn.endswith('.json'):
                continue
            base = os.path.splitext(fn)[0]
            jp = os.path.join(TRANSCRIPTS_DIR, fn)
            try:
                with open(jp, 'r') as f:
                    data = json.load(f)
                before = json.dumps(data, sort_keys=True)
                data2 = _ns.ensure_metadata_in_json(base, data)
                after = json.dumps(data2, sort_keys=True)
                if before != after:
                    count_updated += 1
            except Exception:
                continue
        if count_updated:
            print(f"Backfilled metadata on {count_updated} existing notes.")
    except Exception as e:
        print(f"Metadata backfill skipped: {e}")

    if tasks:
        print(f"Found {len(tasks)} notes to transcribe/title.")
        # Run in background so app startup is not blocked
        async def _runner(tsk_list):
            try:
                # Limit concurrency to avoid API thrashing
                sem = asyncio.Semaphore(3)
                async def _wrap(coro):
                    async with sem:
                        return await coro
                await asyncio.gather(*[_wrap(t) for t in tsk_list])
                print("Background transcription/title generation complete.")
            except Exception as e:
                if "429" in str(e):
                    print("Google API quota exceeded. Background tasks paused.")
                else:
                    print(f"An error occurred during background transcription/title generation: {e}")
        asyncio.create_task(_runner(tasks))
    else:
        print("No missing transcriptions/titles found.")
