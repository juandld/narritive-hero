import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from routes import integrations, models, narratives, notes, programs, folders
from utils import on_startup

logging.basicConfig(level=logging.INFO)
for noisy in [
    "google.generativeai",
    "langchain",
    "langchain_core",
    "langchain_google_genai",
]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(
        config,
        "ALLOWED_ORIGINS",
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost",
            "http://127.0.0.1",
        ],
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/voice_notes",
    StaticFiles(directory=config.VOICE_NOTES_DIR, check_dir=False),
    name="voice_notes",
)

@app.on_event("startup")
async def startup_event():
    await on_startup()

app.include_router(notes.router)
app.include_router(integrations.router)
app.include_router(models.router)
app.include_router(programs.router)
app.include_router(narratives.router)
app.include_router(folders.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
