import os
import json
import shutil
import asyncio
import wave
import contextlib
from datetime import datetime
from services import transcribe_and_save
import usage_log as usage
from note_store import build_note_payload, ensure_metadata_in_json as ensure_metadata_json, save_note_json
import providers
from langchain_core.messages import HumanMessage
import config
from store import get_notes_store

# Centralized paths; keep module vars for monkeypatching in tests
VOICE_NOTES_DIR = config.VOICE_NOTES_DIR
TRANSCRIPTS_DIR = config.TRANSCRIPTS_DIR
NOTES_STORE = get_notes_store()

async def on_startup():
    """On startup, create voice notes dir and backfill any missing transcriptions."""
    if not os.path.exists(VOICE_NOTES_DIR):
        os.makedirs(VOICE_NOTES_DIR)
    if not os.path.exists(TRANSCRIPTS_DIR):
        os.makedirs(TRANSCRIPTS_DIR)
    # Ensure narratives dir exists under storage
    try:
        import config as _cfg
        NARRATIVES_DIR = getattr(_cfg, "NARRATIVES_DIR", os.path.join(_cfg.STORAGE_DIR, "narratives"))
    except Exception:
        NARRATIVES_DIR = os.path.join(config.STORAGE_DIR, "narratives")
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

    tasks = []
    AUDIO_EXTS = ('.wav', '.ogg', '.webm', '.m4a', '.mp3')
    if getattr(config, "STORE_BACKEND", "filesystem") == "filesystem":
        wav_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.lower().endswith(AUDIO_EXTS)}
        json_files = {f for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.json')}

        for wav_file in wav_files:
            base = os.path.splitext(wav_file)[0]
            json_filename = base + '.json'
            if json_filename not in json_files:
                wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                try:
                    payload = build_note_payload(wav_file, base, "", include_length=False)
                    save_note_json(base, payload)
                except Exception:
                    pass
                tasks.append(transcribe_and_save(wav_path))
            else:
                json_path = os.path.join(TRANSCRIPTS_DIR, json_filename)
                try:
                    with open(json_path, 'r') as jf:
                        data = json.load(jf)
                    if data.get('transcription') == 'Transcription failed.':
                        wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                        tasks.append(transcribe_and_save(wav_path))
                except Exception:
                    wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                    tasks.append(transcribe_and_save(wav_path))
    else:
        # Appwrite mode: no local folders to scan; rely on store listings.
        for note in NOTES_STORE.list_notes():
            if (note.get("transcription") or "").strip() == "Transcription failed.":
                filename = note.get("filename")
                if filename:
                    wav_path = os.path.join(VOICE_NOTES_DIR, filename)
                    if os.path.exists(wav_path):
                        tasks.append(transcribe_and_save(wav_path))

    # Ensure metadata fields (language/topics/tags/folder/length/date) exist on all JSONs
    try:
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
                data2 = ensure_metadata_json(base, data)
                after = json.dumps(data2, sort_keys=True)
                if before != after:
                    count_updated += 1
            except Exception:
                continue
        if count_updated:
            print(f"Backfilled metadata on {count_updated} existing notes.")
    except Exception as e:
        print(f"Metadata backfill skipped: {e}")

    # Backfill missing titles where possible
    try:
        async def _gen_title_for(base: str, data: dict):
            try:
                text = (data.get('transcription') or '').strip()
                if not text:
                    # no transcription; set a sensible default
                    data['title'] = data.get('title') or base
                else:
                    msg = HumanMessage(content=[{"type": "text", "text": (
                        "Return exactly one short title (5–8 words) for the transcription below. "
                        "Use the same language as the transcription. Do not include quotes, bullets, markdown, or any extra text. "
                        "Output only the title on a single line.\n\n" + text
                    )}])
                    try:
                        resp, _ = await asyncio.to_thread(providers.invoke_google, [msg])
                        title = providers.normalize_title_output(getattr(resp, 'content', ''))
                    except Exception:
                        try:
                            title = providers.title_with_openai(text)
                        except Exception:
                            title = base
                    data['title'] = title or base
                # persist update
                save_note_json(base, data)
                try:
                    usage.log_usage(event="title_backfill", provider="auto", model="n/a", key_label="n/a", status="success")
                except Exception:
                    pass
            except Exception:
                # ignore failures
                return

        missing = []
        for fn in list(os.listdir(TRANSCRIPTS_DIR)):
            if not fn.endswith('.json'):
                continue
            base = os.path.splitext(fn)[0]
            jp = os.path.join(TRANSCRIPTS_DIR, fn)
            try:
                with open(jp, 'r') as f:
                    data = json.load(f)
                title = (data.get('title') or '').strip()
                # Treat placeholder titles as missing and re-generate
                if (not title) or title.lower() in { 'untitled', 'title generation failed.' }:
                    missing.append((base, data))
            except Exception:
                continue
        if missing:
            print(f"Backfilling missing titles for {len(missing)} notes...")
            sem = asyncio.Semaphore(3)
            async def _run(item):
                async with sem:
                    await _gen_title_for(item[0], item[1])
            await asyncio.gather(*[_run(it) for it in missing])
    except Exception as e:
        print(f"Title backfill skipped: {e}")

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
