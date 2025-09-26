<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let note: {
    filename: string;
    transcription?: string;
    title?: string;
    date?: string;
    length_seconds?: number;
    topics?: string[];
  };
  export let expanded: boolean;
  export let selected: boolean;

  const dispatch = createEventDispatcher();

  import { BACKEND_URL } from '../config';

  // Tag editing state
  let newTagLabel: string = '';
  const TAG_COLORS = [
    { label: 'Red', value: '#EF4444' },
    { label: 'Orange', value: '#F59E0B' },
    { label: 'Green', value: '#10B981' },
    { label: 'Blue', value: '#3B82F6' },
    { label: 'Violet', value: '#8B5CF6' },
    { label: 'Pink', value: '#EC4899' },
    { label: 'Gray', value: '#6B7280' }
  ];
  // Default to last used color from localStorage, otherwise Violet
  let newTagColor: string = (typeof localStorage !== 'undefined' && localStorage.getItem('lastTagColor')) || TAG_COLORS[4].value;
  let showPalette = false;

  async function addTag() {
    const label = newTagLabel.trim();
    if (!label) return;
    const tags = [...(note.tags || []), { label, color: newTagColor }];
    await saveTags(tags);
    newTagLabel = '';
    try { localStorage.setItem('lastTagColor', newTagColor); } catch {}
  }

  async function removeTag(idx: number) {
    const tags = (note.tags || []).filter((_, i) => i !== idx);
    await saveTags(tags);
  }

  async function saveTags(tags: { label: string; color?: string }[]) {
    try {
      await fetch(`${BACKEND_URL}/api/notes/${note.filename}/tags`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags })
      });
      // update local view
      note = { ...note, tags };
    } catch (e) {
      console.error('Failed to save tags', e);
    }
  }

  function selectColor(val: string) {
    newTagColor = val;
    try { localStorage.setItem('lastTagColor', newTagColor); } catch {}
    showPalette = false;
  }

  const MAX_PREVIEW = 140;
  $: previewText = (note.transcription || '').trim();

  function toggleExpand() {
    dispatch('toggle');
  }

  function copyToClipboard() {
    dispatch('copy');
  }

  function deleteNote() {
    dispatch('delete');
  }

  function onSelect() {
    dispatch('select', { filename: note.filename, selected: !selected });
  }
</script>

<li style="margin-bottom: 1.5rem; padding: 1rem; background-color: #f1f3f4; border-radius: 8px;">
  <input type="checkbox" checked={selected} on:change={onSelect} />
  <div style="display:flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;">
    <p style="margin:0; font-weight: 600; font-size: 1rem;">{note.title || note.filename.replace(/\.wav$/i,'')}</p>
    <small style="color:#666;">{note.date}{#if note.length_seconds} • {note.length_seconds}s{/if}</small>
  </div>
  <div style="margin: 0.25rem 0 0.5rem 0; display:flex; gap:0.35rem; flex-wrap: wrap;">
    {#if note.topics && note.topics.length}
      {#each note.topics as t}
        <span style="background:#e8f0fe; color:#1a73e8; padding:2px 6px; border-radius:12px; font-size:0.75rem;">{t}</span>
      {/each}
    {/if}
    {#if note.tags && note.tags.length}
      {#each note.tags as t, i}
        <span style="background:{t.color || '#6B7280'}; color:#fff; padding:2px 8px; border-radius:12px; font-size:0.75rem; display:inline-flex; align-items:center; gap:6px;">
          {t.label}
          <button aria-label="Remove tag" on:click={() => removeTag(i)} style="background:none; border:none; cursor:pointer;">×</button>
        </span>
      {/each}
    {/if}
  </div>

  <div style="display:flex; gap:0.5rem; align-items:center; margin-bottom:0.5rem; flex-wrap: wrap; position: relative;">
    <input aria-label="New tag" placeholder="Add tag" bind:value={newTagLabel} style="flex:1; min-width: 140px; padding:0.35rem 0.5rem; border:1px solid #e5e7eb; border-radius:6px;" />
    <button type="button" aria-label="Selected color" on:click={() => (showPalette = !showPalette)}
      style="width:26px; height:26px; border-radius:50%; border:2px solid #111; background:{newTagColor}; cursor:pointer;">
    </button>
    {#if showPalette}
      <div style="position:absolute; right:64px; bottom:40px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:6px; display:flex; gap:6px; box-shadow:0 10px 20px rgba(0,0,0,0.08);">
        {#each TAG_COLORS as c}
          <button type="button" title={c.label} aria-label={c.label} on:click={() => selectColor(c.value)}
            style="width:22px; height:22px; border-radius:50%; border:2px solid {newTagColor===c.value ? '#111' : '#fff'}; background:{c.value}; cursor:pointer;">
          </button>
        {/each}
      </div>
    {/if}
    <button on:click={addTag} style="background-color:#1a73e8; color:white; border:none; padding:0.45rem 0.8rem; border-radius:6px; cursor:pointer;">Add</button>
  </div>
  <audio controls src="{`${BACKEND_URL}/voice_notes/${note.filename}`}" style="width: 100%; margin-bottom: 0.5rem;"></audio>
  <blockquote style="background-color: white; padding: 0.5rem 1rem; border-left: 5px solid #4285f4; margin: 0; border-radius: 4px;">
    <p>
      {#if note.transcription}
        {expanded ? note.transcription : (previewText.length > MAX_PREVIEW ? previewText.slice(0, MAX_PREVIEW) + '…' : previewText)}
      {:else}
        <em>Transcribing…</em>
      {/if}
    </p>
    {#if previewText && previewText.length > 0}
      <button
        on:click={toggleExpand}
        style="background: none; border: none; color: #4285f4; cursor: pointer; font-size: 0.9em; transform: rotate({expanded ? '180deg' : '0deg'});"
      >
        {expanded ? '\u25B2' : '\u25BC'}
      </button>
    {/if}
  </blockquote>
  <button
    on:click={copyToClipboard}
    style="background-color: #4285f4; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px;"
    >Copy TS</button
  >
  <button
    on:click={deleteNote}
    style="background-color: #db4437; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; margin-left: 10px;"
    >Delete</button
  >
</li>
