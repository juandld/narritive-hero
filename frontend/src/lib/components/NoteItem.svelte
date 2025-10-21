<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let note: {
    filename: string;
    transcription?: string;
    title?: string;
    date?: string;
    length_seconds?: number;
    topics?: string[];
    folder?: string;
    tags?: { label: string; color?: string }[];
  };
  export let expanded: boolean;
  export let selected: boolean;
  export let index: number;
  export let variant: 'full' | 'compact' = 'full';

  const dispatch = createEventDispatcher();

  import { BACKEND_URL } from '../config';
  import AudioPlayer from './AudioPlayer.svelte';
  import ColorPalette from '$lib/components/common/ColorPalette.svelte';
  import { createDragGhost } from '$lib/utils/dnd';

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
  let showTagEditor = false; // allow tags editor in compact view via toggle
  let editingTagIndex: number | null = null;

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

  async function changeTagColor(idx: number, color: string) {
    const tags = (note.tags || []).map((t, i) => i === idx ? { ...t, color } : t);
    await saveTags(tags);
    editingTagIndex = null;
  }

  let editingTagLabel = '';
  function beginRename(idx: number) {
    editingTagIndex = idx;
    editingTagLabel = (note.tags?.[idx]?.label || '').trim();
  }
  async function saveTagLabel(idx: number) {
    const label = editingTagLabel.trim();
    if (!label) return;
    const tags = (note.tags || []).map((t, i) => i === idx ? { ...t, label } : t);
    await saveTags(tags);
    editingTagIndex = null;
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
  $: hasAudio = /\.(wav|ogg|webm|m4a|mp3)$/i.test(note.filename || '');

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

  let dragging = false;
  function onCardClick(e: MouseEvent) {
    if (dragging) { return; }
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

  // Audio state for styling
  let isLoaded = false;
  let isPlaying = false;
</script>

<li draggable="true" on:dragstart={(e)=>{
    dragging = true;
    try{
      const sel = (window as any)?.__selectedNotes;
      const filenames = (selected && sel && typeof sel.size === 'number') ? Array.from(sel) : [note.filename];
      const payload = { filenames };
      // Fallback: if global not set, include just this note
      e.dataTransfer?.setData('application/json', JSON.stringify(payload));
      // Custom drag image with count
      const count = filenames.length;
      const { element: ghost, cleanup } = createDragGhost(count > 1 ? `${count} notes` : `1 note`, '🎵');
      e.dataTransfer?.setDragImage(ghost, 24, 24);
      setTimeout(()=>{ try{ cleanup(); }catch{} }, 0);
      document.body.classList.add('dragging-notes');
    }catch{}
  }} on:dragend={(e)=>{ setTimeout(()=>{ dragging = false; document.body.classList.remove('dragging-notes'); }, 0); }}
  class="card {variant}" class:selected={selected} class:playing={isPlaying} class:loaded={isLoaded}>
  <div class="card-body" role="button" aria-pressed={selected} tabindex="0"
    on:mousedown={(e)=>{ if (!expanded) { e.preventDefault(); } if (e.shiftKey) { e.preventDefault(); try { const s=window.getSelection(); if (s) s.removeAllRanges(); } catch {} } }}
    on:click={onCardClick}
    on:keydown={onCardKey}
  >
  <div class="header">
    <p class="title">{note.title || note.filename.replace(/\.\w+$/i,'')}</p>
    <div class="tools">
      <span class="badge type" title="Type">{hasAudio ? 'Audio' : 'Text'}</span>
      {#if note.language}
        <span class="badge lang" title="Language">{note.language}</span>
      {/if}
      <button class="mini" title="Edit tags" aria-label="Edit tags" on:click|stopPropagation={() => (showTagEditor = !showTagEditor)}>
        🏷️
      </button>
      <small class="meta">{note.date}{#if note.length_seconds} • {note.length_seconds}s{/if}</small>
    </div>
  </div>
  <div class="chips">
    {#if note.topics && note.topics.length}
      {#each note.topics as t}
        <span class="topic" title="AI tag">{t}</span>
      {/each}
    {/if}
    {#if note.tags && note.tags.length}
      {#each note.tags as t, i}
        <span
          class="tag"
          role="button"
          tabindex="0"
          style="background:{t.color || '#6B7280'};"
          on:click|stopPropagation={() => beginRename(i)}
          on:keydown|stopPropagation={(e)=>{ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); beginRename(i); } }}
        >
          {t.label}
          <button aria-label="Remove tag" on:click|stopPropagation={() => removeTag(i)} class="tag-x">×</button>
        </span>
        {#if editingTagIndex === i}
          <div class="tag-inline-editor">
            <input class="rename" bind:value={editingTagLabel} on:click|stopPropagation on:keydown={(e)=>{ if(e.key==='Enter'){ saveTagLabel(i); } }} />
            <ColorPalette colors={TAG_COLORS} selected={(t.color||'')} size="small" ariaLabel="Pick tag color" onPick={(v)=>changeTagColor(i, v)} />
            <button class="mini" on:click={() => saveTagLabel(i)}>Save</button>
            <button class="mini" on:click={() => (editingTagIndex = null)}>Cancel</button>
          </div>
        {/if}
      {/each}
    {/if}
    <!-- Inline add tag chip -->
    <button class="add-chip" on:click|stopPropagation={() => (showTagEditor = !showTagEditor)} aria-expanded={showTagEditor}>+ Tag</button>
    {#if showTagEditor}
      <div class="tag-inline-editor">
        <input class="rename" placeholder="New tag" bind:value={newTagLabel} on:click|stopPropagation on:keydown={(e)=>{ if(e.key==='Enter'){ addTag(); } }} />
        <ColorPalette colors={TAG_COLORS} selected={newTagColor} size="small" ariaLabel="Pick tag color" onPick={(v)=>selectColor(v)} />
        <button class="mini" on:click={addTag}>Add</button>
        <button class="mini" on:click={() => { showTagEditor = false; newTagLabel=''; }}>Cancel</button>
      </div>
    {/if}
  </div>
  {#if hasAudio}
    <AudioPlayer
      src={`${BACKEND_URL}/voice_notes/${encodeURIComponent(note.filename)}`}
      on:play={() => (isPlaying = true)}
      on:pause={() => (isPlaying = false)}
      on:ended={() => (isPlaying = false)}
      on:loaded={() => (isLoaded = true)}
      on:emptied={() => { isLoaded = false; isPlaying = false; }}
    />
  {/if}
  <blockquote class="text">
    <p class:clamp={variant==='compact' && !expanded} class:selectable={expanded} class:noselect={!expanded}>
      {#if note.transcription}
        {expanded ? note.transcription : (previewText.length > MAX_PREVIEW ? previewText.slice(0, MAX_PREVIEW) + '…' : previewText)}
      {:else}
        <em>Transcribing…</em>
      {/if}
    </p>
    {#if previewText && previewText.length > 0}
      <button class="toggle" on:mousedown|stopPropagation on:click|stopPropagation={toggleExpand}>
        {expanded ? '\u25B2' : '\u25BC'}
      </button>
    {/if}
  </blockquote>
  <div class="actions">
    <button class="primary" on:click|stopPropagation={copyToClipboard}>Copy TS</button>
    <button class="danger" on:click|stopPropagation={deleteNote}>Delete</button>
  </div>
  </div>
</li>

<style>
  .card { position: relative; margin-bottom: 1.5rem; padding: 1rem; background-color: #f1f3f4; border-radius: 8px; cursor: pointer; outline: 2px solid transparent; outline-offset: 0; transition: outline-color 120ms ease, box-shadow 120ms ease; }
  .card.compact { margin-bottom: .75rem; padding: .6rem .7rem; }
  .header { display:flex; justify-content: space-between; align-items: baseline; gap: .5rem; flex-wrap: wrap; }
  .title { margin:0; font-weight: 600; font-size: 1rem; }
  .card.compact .title { font-size: .95rem; }
  .meta { color:#666; }
  .tools { display:flex; align-items:center; gap:.35rem; }
  .badge { font-size:.7rem; background:#eef2ff; color:#4338ca; padding:2px 8px; border-radius:9999px; }
  .badge.lang { background:#e8f0fe; color:#1a73e8; }
  .mini { border:1px solid #e5e7eb; background:#fff; color:#374151; border-radius:6px; padding:.15rem .4rem; cursor:pointer; font-size:.85rem; }
  .chips { margin: .25rem 0 .5rem 0; display:flex; gap:.35rem; flex-wrap: wrap; }
  .topic { background:#e8f0fe; color:#1a73e8; padding:2px 10px; border-radius:9999px; font-size:.75rem; }
  .tag { color:#fff; padding:2px 10px; border-radius:9999px; font-size:.75rem; display:inline-flex; align-items:center; gap:6px; border:none; cursor:pointer; }
  .tag .tag-x { background:none; border:none; cursor:pointer; color:#fff; }
  .add-chip { background:#fff; color:#374151; border:1px solid #e5e7eb; border-radius:9999px; padding:2px 10px; cursor:pointer; }
  .tag-inline-editor { display:inline-flex; align-items:center; gap:.35rem; margin-left:.25rem; flex-wrap: wrap; }
  .tag-inline-editor .rename { flex:0 1 200px; border:1px solid #e5e7eb; border-radius:6px; padding:.3rem .45rem; }
  /* removed unused local palette overrides; ColorPalette provides its own styles */
  /* custom audio player replaces native controls */
  .text { background-color:#fff; padding:.5rem 1rem; border-left:5px solid #4285f4; margin:0; border-radius:4px; }
  .text p { margin: .25rem 0; }
  .text p.noselect { user-select: none; -webkit-user-select: none; -ms-user-select: none; }
  .text p.selectable { user-select: text; -webkit-user-select: text; }
  .text p.clamp { display:-webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow:hidden; }
  .toggle { background:none; border:none; color:#4285f4; cursor:pointer; font-size:.9em; transform: rotate(var(--deg, 0deg)); }
  .actions { margin-top: 10px; display:flex; gap:.5rem; }
  .actions .primary { background-color:#4285f4; color:#fff; padding:.5rem 1rem; border:none; border-radius:4px; cursor:pointer; }
  .actions .danger { background-color:#db4437; color:#fff; padding:.5rem 1rem; border:none; border-radius:4px; cursor:pointer; }
  /* Hover state: light blue border to indicate selectability */
  .card:hover { outline-color: #93C5FD; /* tailwind sky-300 */ }
  /* Keyboard focus mirrors hover for accessibility */
  .card-body:focus-visible { outline: 2px solid #93C5FD; box-shadow: 0 0 0 3px rgba(147,197,253,0.35); border-radius: 6px; }
  /* Selected state: solid primary blue border */
  .card.selected { outline-color: #3B82F6; /* tailwind blue-500 */ }

  /* Complementary text accent while loaded/playing, without fighting selection outline */
  .card.loaded:not(.playing) .text { border-left-color:#93C5FD; }
  .card.playing .text { border-left-color:#10B981; }
  /* Dragging visuals */
  :global(body.dragging-notes) .card.selected { opacity: .6; }
</style>
