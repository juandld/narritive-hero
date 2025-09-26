from pydantic import BaseModel
from typing import Optional, List

class Note(BaseModel):
    filename: str
    transcription: Optional[str] = None
    title: Optional[str] = None

class Tag(BaseModel):
    label: str
    color: Optional[str] = None  # hex string like #ff0000

class TagsUpdate(BaseModel):
    tags: List[Tag]
