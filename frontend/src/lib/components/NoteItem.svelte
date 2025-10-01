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
  export let index: number;
  export let variant: 'full' | 'compact' = 'full';

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

  // checkbox removed; selection handled by card click

  function onCardClick(e: MouseEvent) {
    // Toggle selection when clicking on the card background area
    const shift = e.shiftKey === true;
    const next = !selected;
    dispatch('select', { filename: note.filename, selected: next, index, shift });
  }

  function onCardKey(e: KeyboardEvent) {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      const next = !selected;
      dispatch('select', { filename: note.filename, selected: next, index, shift: false });
    }
  }
</script>

<li class="card {variant}" class:selected={selected} on:mousedown={(e)=>{ if (e.shiftKey) { e.preventDefault(); try { const s=window.getSelection(); if (s) s.removeAllRanges(); } catch {} } }} on:click={onCardClick} on:keydown={onCardKey} aria-selected={selected} tabindex="0">
  <div class="header">
    <p class="title">{note.title || note.filename.replace(/\.\w+$/i,'')}</p>
    <small class="meta">{note.date}{#if note.length_seconds} • {note.length_seconds}s{/if}</small>
  </div>
  <div class="chips">
    {#if note.topics && note.topics.length}
      {#each note.topics as t}
        <span class="topic">{t}</span>
      {/each}
    {/if}
    {#if note.tags && note.tags.length}
      {#each note.tags as t, i}
        <span class="tag" style="background:{t.color || '#6B7280'};">
          {t.label}
          <button aria-label="Remove tag" on:click|stopPropagation={() => removeTag(i)} class="tag-x">×</button>
        </span>
      {/each}
    {/if}
  </div>

  <div class="tag-editor" class:hide={variant==='compact'}>
    <input aria-label="New tag" placeholder="Add tag" bind:value={newTagLabel} />
    <button type="button" aria-label="Selected color" class="color" on:click|stopPropagation={() => (showPalette = !showPalette)} style="background:{newTagColor};"></button>
    {#if showPalette}
      <div class="palette" on:click|stopPropagation>
        {#each TAG_COLORS as c}
          <button type="button" title={c.label} aria-label={c.label} on:click={() => selectColor(c.value)} style="background:{c.value}; border-color:{newTagColor===c.value ? '#111' : '#fff'}"></button>
        {/each}
      </div>
    {/if}
    <button on:click|stopPropagation={addTag} class="add">Add</button>
  </div>
  <audio controls src="{`${BACKEND_URL}/voice_notes/${note.filename}`}"></audio>
  <blockquote class="text" on:mousedown={(e) => { if (!expanded) { e.preventDefault(); } }}>
    <p class:clamp={variant==='compact' && !expanded} class:selectable={expanded} class:noselect={!expanded}>
      {#if note.transcription}
        {expanded ? note.transcription : (previewText.length > MAX_PREVIEW ? previewText.slice(0, MAX_PREVIEW) + '…' : previewText)}
      {:else}
        <em>Transcribing…</em>
      {/if}
    </p>
    {#if previewText && previewText.length > 0}
      <button class="toggle" on:click|stopPropagation={toggleExpand}>
        {expanded ? '\u25B2' : '\u25BC'}
      </button>
    {/if}
  </blockquote>
  <div class="actions">
    <button class="primary" on:click|stopPropagation={copyToClipboard}>Copy TS</button>
    <button class="danger" on:click|stopPropagation={deleteNote}>Delete</button>
  </div>
</li>

<style>
  .card { position: relative; margin-bottom: 1.5rem; padding: 1rem; background-color: #f1f3f4; border-radius: 8px; cursor: pointer; }
  .card.compact { margin-bottom: .75rem; padding: .6rem .7rem; }
  .header { display:flex; justify-content: space-between; align-items: baseline; gap: .5rem; flex-wrap: wrap; }
  .title { margin:0; font-weight: 600; font-size: 1rem; }
  .card.compact .title { font-size: .95rem; }
  .meta { color:#666; }
  .chips { margin: .25rem 0 .5rem 0; display:flex; gap:.35rem; flex-wrap: wrap; }
  .topic { background:#e8f0fe; color:#1a73e8; padding:2px 6px; border-radius:12px; font-size:.75rem; }
  .tag { color:#fff; padding:2px 8px; border-radius:12px; font-size:.75rem; display:inline-flex; align-items:center; gap:6px; }
  .tag .tag-x { background:none; border:none; cursor:pointer; color:#fff; }
  .tag-editor { display:flex; gap:.5rem; align-items:center; margin-bottom:.5rem; flex-wrap: wrap; position: relative; }
  .tag-editor.hide { display:none; }
  .tag-editor input { flex:1; min-width:140px; padding:.35rem .5rem; border:1px solid #e5e7eb; border-radius:6px; }
  .tag-editor .color { width:26px; height:26px; border-radius:50%; border:2px solid #111; cursor:pointer; }
  .tag-editor .palette { position:absolute; right:64px; bottom:40px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:6px; display:flex; gap:6px; box-shadow:0 10px 20px rgba(0,0,0,0.08); }
  .tag-editor .palette button { width:22px; height:22px; border-radius:50%; border:2px solid #fff; cursor:pointer; }
  audio { width:100%; margin-bottom:.5rem; }
  .text { background-color:#fff; padding:.5rem 1rem; border-left:5px solid #4285f4; margin:0; border-radius:4px; }
  .text p { margin: .25rem 0; }
  .text p.noselect { user-select: none; -webkit-user-select: none; -ms-user-select: none; }
  .text p.selectable { user-select: text; -webkit-user-select: text; }
  .text p.clamp { display:-webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow:hidden; }
  .toggle { background:none; border:none; color:#4285f4; cursor:pointer; font-size:.9em; transform: rotate(var(--deg, 0deg)); }
  .actions { margin-top: 10px; display:flex; gap:.5rem; }
  .actions .primary { background-color:#4285f4; color:#fff; padding:.5rem 1rem; border:none; border-radius:4px; cursor:pointer; }
  .actions .danger { background-color:#db4437; color:#fff; padding:.5rem 1rem; border:none; border-radius:4px; cursor:pointer; }
  .card.selected { outline: 2px solid #3B82F6; outline-offset: 0; }
</style>
