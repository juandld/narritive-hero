import os
import json
import shutil
import asyncio
import wave
import contextlib
from datetime import datetime
from services import transcribe_and_save
import usage_log as usage

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_NOTES_DIR = os.path.join(APP_DIR, "voice_notes")
TRANSCRIPTS_DIR = os.path.join(APP_DIR, "transcriptions")

async def on_startup():
    """On startup, create voice notes dir and backfill any missing transcriptions."""
    if not os.path.exists(VOICE_NOTES_DIR):
        os.makedirs(VOICE_NOTES_DIR)
    if not os.path.exists(TRANSCRIPTS_DIR):
        os.makedirs(TRANSCRIPTS_DIR)
    # titles directory is deprecated; we will migrate any leftover files below
    # Ensure usage logging directory/files exist
    usage.ensure_usage_paths()
    
    print("Checking for missing transcriptions...")
    # Migrate any stray .txt from voice_notes to transcriptions
    for f in list(os.listdir(VOICE_NOTES_DIR)):
        if f.endswith('.txt'):
            src = os.path.join(VOICE_NOTES_DIR, f)
            dst = os.path.join(TRANSCRIPTS_DIR, f)
            try:
                if not os.path.exists(dst):
                    shutil.move(src, dst)
                else:
                    # If both exist, keep the longer content as canonical in dst, then remove src
                    with open(src, 'r') as fs, open(dst, 'r') as fd:
                        s_content = fs.read()
                        d_content = fd.read()
                    keep = s_content if len(s_content) >= len(d_content) else d_content
                    with open(dst, 'w') as fdw:
                        fdw.write(keep)
                    os.remove(src)
            except Exception as e:
                print(f"Warning: could not migrate {src} -> {dst}: {e}")

    # Consolidate any legacy .title files into JSON, prefer from titles/ then voice_notes/
    titles_dir = os.path.join(APP_DIR, "titles")
    def consolidate_title_file(path: str):
        base = os.path.basename(path)
        if not base.endswith('.title'):
            return
        base_no_ext = base[:-6]
        wav_file = base_no_ext + '.wav'
        json_filename = base_no_ext + '.json'
        json_path = os.path.join(TRANSCRIPTS_DIR, json_filename)
        # Load existing JSON if present
        data = None
        if os.path.exists(json_path):
            try:
                import json as _json
                with open(json_path, 'r') as jf:
                    data = _json.load(jf)
            except Exception:
                data = None
        # Read title text
        try:
            with open(path, 'r') as ft:
                title_text = ft.read()
        except Exception:
            title_text = ''
        # If no JSON, build from wav + optional legacy txt
        if not data:
            import json as _json
            txt_path = os.path.join(TRANSCRIPTS_DIR, base_no_ext + '.txt')
            transcription = ''
            if os.path.exists(txt_path):
                try:
                    with open(txt_path, 'r') as f:
                        transcription = f.read()
                except Exception:
                    transcription = ''
            audio_path = os.path.join(VOICE_NOTES_DIR, wav_file)
            try:
                mtime = os.path.getmtime(audio_path)
                date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            except Exception:
                date_str = None
            # duration helper
            def _audio_length_seconds(path: str) -> float | None:
                try:
                    with contextlib.closing(wave.open(path, 'rb')) as wf:
                        frames = wf.getnframes()
                        rate = wf.getframerate()
                        return round(frames / float(rate), 2) if rate else None
                except Exception:
                    return None
            length_sec = _audio_length_seconds(audio_path)
            # topics helper
            def _infer_topics(text: str | None, title: str | None) -> list[str]:
                STOPWORDS = set(
                    "the a an and or but for with without on in at to from of by this that those these is are was were be been being i you he she it we they them me my your our their as not just into over under again more most some any few many much very can could should would".split()
                )
                src = (title or "").strip() or (text or "").strip()
                if not src:
                    return []
                import re
                words = re.findall(r"[A-Za-z]{3,}", src.lower())
                words = [w for w in words if w not in STOPWORDS]
                freq = {}
                for w in words:
                    freq[w] = freq.get(w, 0) + 1
                return sorted(freq, key=lambda k: (-freq[k], k))[:3]
            topics = _infer_topics(transcription, title_text)
            data = {
                "filename": wav_file,
                "title": title_text,
                "transcription": transcription,
                "date": date_str,
                "length_seconds": length_sec,
                "topics": topics,
            }
            with open(json_path, 'w') as jf:
                _json.dump(data, jf, ensure_ascii=False)
            # Remove legacy txt if existed
            if os.path.exists(txt_path):
                os.remove(txt_path)
        else:
            # Merge title into existing JSON if missing/shorter
            try:
                import json as _json
                keep_title = title_text if len(title_text) > len(data.get('title') or '') else data.get('title')
                data['title'] = keep_title or ''
                with open(json_path, 'w') as jf:
                    _json.dump(data, jf, ensure_ascii=False)
            except Exception:
                pass
        # Remove legacy title
        try:
            os.remove(path)
        except Exception:
            pass

    # Consolidate titles from titles/ if present
    if os.path.isdir(titles_dir):
        for f in list(os.listdir(titles_dir)):
            if f.endswith('.title'):
                consolidate_title_file(os.path.join(titles_dir, f))
        # Attempt to remove directory if empty
        try:
            os.rmdir(titles_dir)
        except Exception:
            pass
    # Also consolidate any stray .title in voice_notes/
    for f in list(os.listdir(VOICE_NOTES_DIR)):
        if f.endswith('.title'):
            consolidate_title_file(os.path.join(VOICE_NOTES_DIR, f))

    wav_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.wav')}
    json_files = {f for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.json')}
    txt_files = {f for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.txt')}
    # title_files no longer used; titles are consolidated into JSON

    tasks = []
    for wav_file in wav_files:
        json_filename = wav_file.replace('.wav', '.json')
        txt_filename = wav_file.replace('.wav', '.txt')
        title_filename = wav_file.replace('.wav', '.title')
        # Create combined JSON if missing, otherwise schedule (re)transcription as needed
        if json_filename not in json_files:
            # If we have legacy pieces, consolidate into JSON
            txt_path = os.path.join(TRANSCRIPTS_DIR, txt_filename)
            title_path = os.path.join(APP_DIR, 'titles', title_filename)
            title = None
            transcription = None
            if os.path.exists(txt_path):
                with open(txt_path, 'r') as f:
                    transcription = f.read()
            if os.path.exists(title_path):
                with open(title_path, 'r') as f:
                    title = f.read()
            if title is not None or transcription is not None:
                # compute metadata
                audio_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                try:
                    mtime = os.path.getmtime(audio_path)
                    date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                except Exception:
                    date_str = None
                # duration
                def _audio_length_seconds(path: str) -> float | None:
                    try:
                        with contextlib.closing(wave.open(path, 'rb')) as wf:
                            frames = wf.getnframes()
                            rate = wf.getframerate()
                            return round(frames / float(rate), 2) if rate else None
                    except Exception:
                        return None
                length_sec = _audio_length_seconds(audio_path)
                # simple topics
                def _infer_topics(text: str | None, title: str | None) -> list[str]:
                    STOPWORDS = set(
                        "the a an and or but for with without on in at to from of by this that those these is are was were be been being i you he she it we they them me my your our their as not just into over under again more most some any few many much very can could should would".split()
                    )
                    src = (title or "").strip() or (text or "").strip()
                    if not src:
                        return []
                    import re
                    words = re.findall(r"[A-Za-z]{3,}", src.lower())
                    words = [w for w in words if w not in STOPWORDS]
                    freq = {}
                    for w in words:
                        freq[w] = freq.get(w, 0) + 1
                    return sorted(freq, key=lambda k: (-freq[k], k))[:3]

                topics = _infer_topics(transcription, title)
                payload = {
                    "filename": wav_file,
                    "title": title or "",
                    "transcription": transcription or "",
                    "date": date_str,
                    "length_seconds": length_sec,
                    "topics": topics,
                    "tags": [],
                }
                with open(os.path.join(TRANSCRIPTS_DIR, json_filename), 'w') as jf:
                    json.dump(payload, jf, ensure_ascii=False)
                # Remove legacy files after consolidation
                if os.path.exists(txt_path):
                    os.remove(txt_path)
                if os.path.exists(title_path):
                    os.remove(title_path)
            else:
                wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                tasks.append(transcribe_and_save(wav_path))
        else:
            # JSON exists: consider it complete and do not re-transcribe on startup.
            # Users can delete the JSON to force reprocessing.
            continue

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
