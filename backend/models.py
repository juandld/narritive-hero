from pydantic import BaseModel
from typing import Optional

class Note(BaseModel):
    filename: str
    transcription: Optional[str] = None
    title: Optional[str] = None
