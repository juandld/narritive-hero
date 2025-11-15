# Program Registry Guide

The program registry is the shared map that keeps categorization, search, and human workflows aligned. Every entry lives in `storage/programs/programs.json` and describes a durable initiative or bucket you want notes to land in.

## Schema

Each entry is a JSON object with the fields below. Only `key` is strictly required, but strong metadata keeps classification explainable.

| Field | Type | Notes |
| --- | --- | --- |
| `key` | string | Unique slug (lowercase, underscores). Never reuse a key. |
| `title` | string | Human-friendly name. If omitted we fallback to a title-cased key. |
| `description` | string | One-sentence summary of the initiative. Helps humans understand the bucket. |
| `domain` | string | High-level grouping. Allowed: `programming`, `operations`, `personal`, `general`, `research`, `marketing`. Defaults to `general`. |
| `keywords` | string[] | Terms/phrases that should count as strong signals. Lowercase preferred. Comma-separated strings are accepted. |
| `tags` | string[] | Optional lightweight badges (e.g., `frontend`, `ai`). Used for filtering/display, not scoring. |
| `aliases` | string[] | Alternative names to catch free-form references. |
| `owners` | string[] | People accountable for this program. Useful for routing or future notifications. |
| `status` | string | Lifecycle flag (`active`, `incubating`, `paused`, etc.). Defaults to `active`. |
| `filename_prefix` | string | Optional, used when auto-generating filenames or grouping exports. |
| `color` | string | Hex color for UI accents. Optional. |

You can safely add new optional fields; the loader preserves unknown keys so future tooling can adopt them.

## Editing Workflow

1. Duplicate an existing entry in `storage/programs/programs.json`.
2. Pick a new `key` (lowercase, underscores). Keys should be permanent.
3. Add focused keywords. Think about the words or phrases you would actually say in a voice note when this program is relevant.
4. Keep descriptions short but actionable. Mention the outcome or scope.
5. Run `python backend/scripts/validate_programs.py` *(coming soon)* or reload the backend to confirm no validation errors.

### Keyword Tips

- Mix nouns and verbs: `deploy`, `transcription`, `pipeline`, `telegram`.
- Include common synonyms or abbreviations in `aliases`.
- Avoid broad words (`work`, `project`) unless absolutely necessary—they introduce false positives.

### Example Entry

```json
{
  "key": "capture_ux",
  "title": "Capture UX",
  "description": "Voice and text capture experience: recorder, waveform feedback, uploads, and onboarding polish.",
  "domain": "programming",
  "keywords": ["recorder", "waveform", "microphone", "upload", "frontend", "svelte", "capture"],
  "tags": ["frontend", "ux"],
  "aliases": ["capture-experience", "recording-ux"],
  "owners": ["david"],
  "status": "active",
  "filename_prefix": "cap",
  "color": "#10B981"
}
```

## Seeding New Environments

The repository ships with a starter registry aligned to the current roadmap (`inbox`, `capture_ux`, `transcription_pipeline`, `telegram_companion`, `founder_notebook`). Add or prune entries to match your workspace, then commit the JSON file so other agents stay in sync.

If you need a blank slate, delete `storage/programs/programs.json` and restart the backend—it will recreate the directory and fall back to an empty registry.
