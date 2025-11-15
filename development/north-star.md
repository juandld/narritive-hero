# Narrative Hero • North-Star Guide

## Purpose
- Serve as the always-on reference for Narrative Hero’s mission, scope, and active direction.
- Keep every contributor (human or AI) aligned on the experience we are building: frictionless capture of thoughts that quickly become organized, actionable knowledge.
- Summarize the truths scattered through `README.md`, recent updates, and live requirements so agents can ramp instantly.

## Product Vision
- Enable rapid voice-first journaling: the user should feel safe to “just talk” and trust the system to capture, transcribe, title, and organize every idea.
- Default to explainability: any automated step (transcription, titles, categorization, telegram feedback) must echo back what happened so users stay confident.
- Treat voice notes as building blocks for larger narratives—iteration workflows, summaries, and future AI assistance build on these atoms.

## Pillars & Current Capabilities
- **Capture**: Record in-browser or upload audio/video (`.wav/.mp3/.ogg/.webm/.m4a/.mp4`). Frontend shows a live waveform and recording indicator (`svelte-audio-waveform`) so users know we are listening.
- **Transcribe & Title**: Background FastAPI job using Gemini 2.5 Flash (key rotation) with OpenAI fallbacks via LangChain. Metadata stored per note in JSON.
- **Organize**: Notes carry folders, tags, generated topics, and language inference. Narratives can be stitched together or regenerated with extra context.
- **Feedback Loop**: `/api/integrations/telegram` accepts text or audio directly from Telegram (and other callers with a shared token), returning structured acknowledgements (`status`, `transcription_status`, `summary`, etc.) so automations can respond like a real teammate.
- **Storage Layout** (relative to `STORAGE_DIR`):
  - `voice_notes/` – original or normalized audio.
  - `transcriptions/` – JSON per note (metadata, transcription, tags).
  - `narratives/` – generated `.txt` narratives and optional `meta/` titles.
  - `formats/` & `folders/` – saved generation presets and folder registry.

## Active Initiatives (Nov 2024)
1. **Category Intelligence**: Every discrete voice note should auto-land in the right folder/tag. Requirements:
   - Respect existing folder taxonomy; fall back to `Inbox`/uncategorized with rationale when uncertain.
   - Surface the decision in webhook/UI responses so humans can correct it (future feedback loop).
   - Keep the pipeline modular so other agents can plug in custom taxonomies or scoring.
2. **Telegram “Human-in-the-loop” Experience**:
   - Continue improving the webhook response text (“Saved in X; tags Y; Snapshot …”) so the user receives empathetic, concise confirmation.
   - Keep multipart + JSON compatibility so other automation runners can plug in easily.
3. **Resilience & Observability**:
   - Maintain the Gemini→OpenAI fallback pattern throughout new features.
   - Log key decisions (folder choice, summary text) for auditing.

## Technical Ground Rules
- **Frontend**: SvelteKit + TypeScript; keep UI states obvious (recording indicator, uploading, polling). Prefer lightweight comments only for complex logic.
- **Backend**: FastAPI; avoid blocking operations. Background tasks handle transcription. Shared helpers (`_create_note_from_text_payload`, `_summarize_text_snippet`, `_parse_tags`) should stay generic for reuse across integrations.
- **API Contracts**: When enhancing endpoints, return machine- and human-readable fields (`status`, `feedback`, `summary`, `tags`, `folder`). Include failure modes (`transcription_status = failed`).
- **Security & Extensibility**: Secrets via `.env`; webhook token optional but supported. Keep IO bounded to `STORAGE_DIR`.

## Hand-off Checklist for New Agents
1. Read this file, then skim `README.md` for command specifics.
2. Confirm local dev setup (`./dev.sh` or manual commands) and that `storage/` is writable.
3. Review `frontend/src/lib/components/NarrativeIterateModal.svelte` and `backend/main.py` sections noted above for waveform UX and Telegram integration.
4. When adding features:
   - Update this file if the project direction changes.
   - Reflect new API schemas in `README.md` (API docs section).
   - Preserve the “north star”: effortless capture → transparent organization → narrative-ready knowledge.

## Future North Star Milestones
- Automatic categorization with explainable reasoning and user-tunable rules.
- Narrative iteration that leverages categorized notes to propose structured strategic updates.
- Agent-friendly context hub (this folder) that stays current without relying on tribal knowledge.

Stay aligned with these principles, and every enhancement moves Narrative Hero closer to being that ever-present, trusted collaborator for stream-of-consciousness productivity.
