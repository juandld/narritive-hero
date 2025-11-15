# Narrative Hero • Project Status & Needs

Updated: 2024-11-02

## Snapshot
- **Core value**: frictionless capture → transparent organization → narrative-ready output.
- **Latest additions**:
  - Frontend recorder now shows a live waveform + recording indicator (via `svelte-audio-waveform`).
- Telegram webhook accepts text *and* audio, responds with status, summaries, and tag/folder info.
  - Smoke test suite covers `/api/notes`, `/api/narratives/generate`, and transcription pipeline.
  - `development/north-star.md` codifies mission, pillars, and onboarding steps for agents.

## Current Health
| Area | Status | Notes |
| --- | --- | --- |
| Capture UX | ✅ Shipping | Visual feedback while recording; upload/record parity preserved. |
| Transcription/Title pipeline | ✅ Stable | Gemini primary, OpenAI fallback; telemetry logged. |
| Telegram integration | ✅ Beta | Text + audio supported, returns structured feedback; awaiting categorization tie-ins. |
| Automated categorization | ⚠️ Pending | Tags/folders set manually or via webhook payload; no LLM-driven classification yet. |
| Testing | ⚠️ Minimal | Smoke tests pass; full pytest suite requires installing dev deps. |
| Documentation | ✅ Improving | README + north star; status tracked here. |

## Immediate Needs
1. **Intelligent Categorization**
   - Detect domain (programming vs. operations vs. personal).
   - Map programming notes to the correct project/program with explanation.
   - Surface decisions in webhook/UI, allow user override, log feedback.
2. **Program Registry**
   - Maintain authoritative list of initiatives (e.g., “AI pipeline”, “Frontend polish”).
   - Store in config/JSON so agents and categorizer share the same source.
3. **Testing Depth**
   - Restore full pytest coverage once deps are available.
   - Add integration tests for Telegram audio flow once transcription jobs can be awaited deterministically.
4. **Telemetry & Observability**
   - Record categorization decisions and summarization results for auditing.
   - Consider lightweight dashboards or log aggregation for webhook interactions.

## Near-Term Roadmap
- **Week 1**: Ship categorizer service (LLM prompt + fallback heuristics), wire into webhook + background tasks.
- **Week 2**: Expose categorization results in frontend note cards; enable corrections that retrain weighting.
- **Week 3**: Expand test suite, add regression coverage for program assignments, validate across sample transcripts.

## References
- North star / foundational guidance: `development/north-star.md`
- Frontend recording component: `frontend/src/lib/components/NarrativeIterateModal.svelte`
- Telegram webhook + summary helpers: `backend/main.py` (`_create_note_from_text_payload`, `_summarize_text_snippet`, `/api/integrations/telegram`)
- Telegram companion roadmap: `development/telegram-companion.md`
- Smoke tests entry point: `tests/backend/test.sh`
