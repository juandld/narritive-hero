"""
Storage backend interfaces.

This module defines the abstract operations required by Narrative Hero. The
current filesystem-backed implementation (note_store.py) satisfies these
operations directly; upcoming Appwrite adapters can implement the same interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional, Tuple


class NotesStore(ABC):
    """Abstract interface for persisting note metadata + audio references."""

    @abstractmethod
    def save_note(self, base_id: str, payload: Dict[str, Any]) -> None:
        """Persist/update note metadata keyed by base_id."""

    @abstractmethod
    def load_note(self, base_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        """Return (data, transcription, title) for base_id."""

    @abstractmethod
    def list_notes(self) -> Iterable[Dict[str, Any]]:
        """Yield note dictionaries (metadata + transcription)."""

    @abstractmethod
    def delete_note(self, base_id: str) -> None:
        """Delete metadata for base_id."""
