# Telegram Companion • Delivery Plan

The Telegram companion is the empathetic “human-in-the-loop” surface that keeps founders looped in while our categorization intelligence matures. This plan breaks the work into clear stages so every note received in Telegram is captured, transcribed, classified, and searchable without losing the personal touch.

## Goals
- **Trust**: Every voice or text note sent to the bot should acknowledge receipt, confirm where it lives, and explain any automation that occurred.
- **Organization**: Notes should inherit folders/programs, tags, and rationales that mirror the in-app experience.
- **Recall**: Telegram threads should be easy to revisit, with links or identifiers that map back to the web UI and upcoming global search.
- **Extensibility**: Keep the webhook JSON responses stable so other automation runners (e.g., Zapier, custom scripts) can leverage the same pipeline.

## Current Snapshot
- ✅ Voice + text ingestion with resilient downloads and transcription fallbacks.
- ✅ Status replies gated on completed transcription, with generated titles and curated tags.
- ⚠️ Categorization: heuristics exist but lack program registry integration and confidence/rationale in the Telegram reply.
- ⚠️ Searchability: no quick way to jump from Telegram back to specific notes or filter by categories.

## Phase Breakdown

### Phase 1: Categorization Alignment
1. **Registry Integration**  
   - Load `storage/programs/programs.json` at webhook start.  
   - Inject `auto_program`, `auto_category`, and confidences into Telegram replies when available.  
   - Include short rationales (“Matched keywords: deploy, FastAPI.”) and link to the registry entry (by `key`) so humans can confirm intent.
2. **Fallback Paths**  
   - If confidence < threshold, default to `inbox` and mark the reply with “Needs review.”  
   - Add `/api/integrations/telegram/review` endpoint to bump low-confidence notes into a manual queue (writes `needs_review: true` into JSON).

### Phase 2: Recall & Linking
1. **Deep Links**  
   - Add `note_url` to Telegram responses using the public frontend host (`https://frontend.camofiles.app/notes/<filename>`).  
   - Ensure links gracefully handle notes that have not yet been fully processed (show pending state).
2. **Threaded Follow-ups**  
   - When a note is updated (tag change, categorization correction), send a Telegram edit or follow-up message referencing the original chat message ID.  
   - Store `telegram_message_id` in the note JSON to reduce duplicate notifications.

### Phase 3: Personalization & Search Hooks
1. **Quick Summaries**  
   - Offer `/summary` command that replays the last N notes with titles + categories (leveraging future search index).  
   - Provide `/program <key>` to fetch the latest notes for a specific program via the search API.
2. **Adaptive Tone**  
   - Let users opt into more/less verbose replies via `/settings` command (stored per Telegram `chat_id` in a lightweight JSON).  
   - Respect silent hours or “digest” mode to bundle multiple notes into one daily summary.

### Phase 4: Automation & Telemetry
1. **Event Logging**  
   - Emit structured logs for each Telegram interaction (request, categorization result, follow-up timing).  
   - Ship a small dashboard or CLI summary (`python backend/scripts/telegram_report.py`) highlighting average turnaround time, failures, and category distribution.
2. **Self-Healing Hooks**  
    - Detect repeated failures (e.g., download errors) and auto-reply with remediation steps or escalate to an owner listed in the program registry.  
    - Add circuit breakers if the transcription service is degraded; queue messages and notify users once recovered.

## Text-as-Query Plan
Voice memos remain the primary capture mechanism. Plain text messages to the bot should feel like conversational search—not new note creation. We will pivot text handling to operate in “query mode” with an explicit command to force capture when needed.

### Stage A: Command & Query Routing
- Treat `/capture`, `/note`, or `/text` commands as the only triggers for text-to-note creation.  
- Any other plain text input routes through the upcoming search API (`/api/search`) and returns relevant notes with titles, tags, and links.  
- Support quick filters in-line (e.g., `program:telegram voice pipeline`).

### Stage B: Response Templates
- Return top matches (configurable, default 3) with short snippets and buttons/links to open in the web UI.  
- Include a “Didn’t find it?” hint that suggests sending a voice memo or using `/capture` to store the text verbatim.

### Stage C: Historical Context
- Cache the last few queries per `chat_id` so follow-up questions like “What about this week?” can append context before hitting search.  
- Allow `/refine` or simple replies with modifiers (“show personal only”) to rerun the previous query with added filters.

### Stage D: Telemetry & Opt-out
- Log query vs. capture ratios to ensure we’re meeting the “ideas on tap” goal and adjust UX accordingly.  
- Provide `/settings text-mode capture|query` to let power users toggle back to text capture if desired; default remains `query`.

This shift keeps Telegram aligned with the voice-first mission while turning text into a fast gateway for recall and cross-referencing.

## Dependencies & Interfaces
- **Program Registry**: Must stay synchronized with categorizer logic; changes trigger revalidation of Telegram flows.  
- **Search API (upcoming)**: Telegram commands will hit the same `/api/search` endpoint planned for the web UI.  
- **Secrets**: Encourage use of `TELEGRAM_WEBHOOK_SECRET` and `TELEGRAM_INGEST_TOKEN`; document how to rotate tokens without downtime.

## Definition of Done
- All phases tracked in project status with clear owner.  
- Telegram replies always include title, tags/program (when confident), and helpful links.  
- Users can resolve low-confidence notes entirely within Telegram (either via commands or follow-up prompts).  
- Observability in place to monitor transcription timings, categorization confidence, and error rates.

Revisit this plan after each milestone to fold in user feedback and new product direction.
