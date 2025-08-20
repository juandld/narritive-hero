import os
import base64
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# --- Transcription Model ---
# Make sure your GOOGLE_API_KEY is set in the .env file
# Using a model that supports audio input
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

async def generate_title(prompt: str, llm_instance) -> str:
    """Generates a concise title from the given prompt."""
    print("Generating title...")
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": prompt,
            }
        ]
    )
    response = await llm_instance.ainvoke([message])
    title = response.content.strip()
    print(f"Generated title: {title}")
    return title

async def transcribe_and_save(wav_path: str):
    """Transcribes a single audio file and saves the transcription."""
    txt_path = wav_path.replace('.wav', '.txt')
    print(f"Transcribing {os.path.basename(wav_path)}...")

    with open(wav_path, "rb") as audio_file:
        audio_bytes = audio_file.read()

    encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')

    transcription_prompt = "Transcribe this audio recording accurately."

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": transcription_prompt,
            },
            {
                "type": "media",
                "mime_type": "audio/wav",
                "data": encoded_audio,
            },
        ]
    )

    response = await llm.ainvoke([message])
    transcription = response.content

    with open(txt_path, 'w') as f:
        f.write(transcription)
    print(f"Finished transcribing {os.path.basename(wav_path)}.")

    # Generate and save title
    try:
        title_prompt = f"Generate a concise title (under 10 words) for the following audio transcription:\n\n{transcription}"

        title = await generate_title(title_prompt, llm)
        title_path = wav_path.replace('.wav', '.title')
        with open(title_path, 'w') as f:
            f.write(title)
    except Exception as e:
        print(f"Error generating title for {os.path.basename(wav_path)}: {e}")
        title_path = wav_path.replace('.wav', '.title')
        with open(title_path, 'w') as f:
            f.write("Title generation failed.")
