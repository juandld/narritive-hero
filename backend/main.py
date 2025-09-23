from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from services import process_interaction
import uvicorn

app = FastAPI()

# Configure CORS to allow requests from the SvelteKit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # The default SvelteKit dev server address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/narrative/interaction")
async def handle_interaction(
    audio_file: UploadFile = File(...), 
    current_scenario_id: str = Form(...)
):
    """
    This endpoint receives audio and the current scenario ID,
    processes them, and returns the next scenario.
    """
    result = process_interaction(audio_file.file, current_scenario_id)
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
