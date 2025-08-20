import os
import asyncio
from services import transcribe_and_save

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_NOTES_DIR = os.path.join(APP_DIR, "voice_notes")

async def on_startup():
    """On startup, create voice notes dir and backfill any missing transcriptions."""
    if not os.path.exists(VOICE_NOTES_DIR):
        os.makedirs(VOICE_NOTES_DIR)
    
    print("Checking for missing transcriptions...")
    wav_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.wav')}
    txt_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.txt')}
    title_files = {f for f in os.listdir(VOICE_NOTES_DIR) if f.endswith('.title')}

    tasks = []
    for wav_file in wav_files:
        txt_filename = wav_file.replace('.wav', '.txt')
        title_filename = wav_file.replace('.wav', '.title')
        if txt_filename not in txt_files or title_filename not in title_files:
            wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
            tasks.append(transcribe_and_save(wav_path))
        else:
            # Check if the transcription failed
            transcription_path = os.path.join(VOICE_NOTES_DIR, txt_filename)
            if os.path.exists(transcription_path):
                with open(transcription_path, 'r') as f:
                    transcription = f.read()
                if transcription == "Transcription failed.":
                    wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                    tasks.append(transcribe_and_save(wav_path))
            
            # Check if title generation failed
            title_path = os.path.join(VOICE_NOTES_DIR, title_filename)
            if os.path.exists(title_path):
                with open(title_path, 'r') as f:
                    title_content = f.read()
                if title_content == "Title generation failed.":
                    wav_path = os.path.join(VOICE_NOTES_DIR, wav_file)
                    tasks.append(transcribe_and_save(wav_path))

    if tasks:
        print(f"Found {len(tasks)} notes to transcribe/title.")
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            if "429" in str(e):
                print("Google API quota exceeded. Please upgrade your plan.")
            else:
                print(f"An error occurred during startup transcription/title generation: {e}")
    else:
        print("No missing transcriptions/titles found.")
