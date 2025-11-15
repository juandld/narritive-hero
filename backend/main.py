import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from routes import integrations, models, narratives, notes, programs, folders
from utils import on_startup

LOG_LEVEL_NAME = getattr(config, "LOG_LEVEL", "INFO") or "INFO"
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME.upper(), logging.INFO)
LOG_FORMAT = (
    '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
    if getattr(config, "LOG_JSON", False)
    else "%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

for noisy in (
    "google.generativeai",
    "langchain",
    "langchain_core",
    "langchain_google_genai",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
):
    logging.getLogger(noisy).setLevel(LOG_LEVEL)

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
