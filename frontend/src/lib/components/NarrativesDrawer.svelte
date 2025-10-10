<script lang="ts">
  import { onMount } from 'svelte';

  type Narrative = {
    filename: string;
    content?: string;
  };

  export let isOpen: boolean;
  export let onClose: () => void;
  export let initialSelect: string | null = null;

  let narratives: Narrative[] = [];
  let selectedNarrative: Narrative | null = null;
  let selectedHtml: string = '';

  import { BACKEND_URL } from '../config';
  import NarrativeIterateModal from './NarrativeIterateModal.svelte';

  let isIterateOpen: boolean = false;
  let selectedExcerpt: string = '';
  let renderEl: HTMLDivElement | null = null;
  let thread: { files: string[]; index: number } = { files: [], index: 0 };

  async function getNarratives() {
    try {
      const response = await fetch(`${BACKEND_URL}/api/narratives`);
      if (response.ok) {
        const filenames: string[] = await response.json();
        narratives = filenames.map((filename) => ({ filename }));
      } else {
        console.error('Failed to fetch narratives:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to fetch narratives:', error);
    }
  }

  async function getNarrativeContent(filename: string) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/narratives/${filename}`);
      if (response.ok) {
        const data = await response.json();
        selectedNarrative = { filename, content: data.content };
        try {
          const tr = await fetch(`${BACKEND_URL}/api/narratives/thread/${filename}`);
          if (tr.ok) {
            thread = await tr.json();
          } else {
            thread = { files: [filename], index: 0 };
          }
        } catch (_) {
          thread = { files: [filename], index: 0 };
        }
      } else {
        console.error('Failed to fetch narrative content:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to fetch narrative content:', error);
    }
  }

  async function deleteNarrative(filename: string) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/narratives/${filename}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        console.log('Delete successful');
        selectedNarrative = null;
        await getNarratives(); // Refresh the list
      } else {
        console.error('Delete failed');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
    }
  }

  onMount(() => {
    if (isOpen) {
      getNarratives();
    }
  });

  $: if (isOpen) {
    getNarratives();
  }

  // If parent provides an initial filename to select, fetch its content when open
  $: if (isOpen && initialSelect) {
    getNarrativeContent(initialSelect);
  }

  // --- Lightweight, safe Markdown rendering ---
  function escapeHtml(s: string): string {
    return s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function renderMarkdownSafe(text: string): string {
    if (!text) return '';
    // Normalize any escaped newlines like "\n" to real newlines
    let t = text.replace(/\\n/g, '\n');
    // Normalize CRLF
    t = t.replace(/\r\n/g, '\n');
    // Escape HTML
    t = escapeHtml(t);

    // Basic inline formatting after escaping (<, >, & already encoded)
    const inline = (s: string) => {
      // Bold **text** or __text__
      s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      s = s.replace(/__([^_]+)__/g, '<strong>$1</strong>');
      // Italic *text* or _text_ (avoid matching bold markers)
      s = s.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, '$1<em>$2</em>');
      s = s.replace(/(^|[^_])_([^_]+)_(?!_)/g, '$1<em>$2</em>');
      return s;
    };

    const lines = t.split(/\n/);
    const out: string[] = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      // Headings
      if (/^###\s+/.test(line)) {
        out.push(`<h3>${inline(line.replace(/^###\s+/, ''))}</h3>`);
        i++; continue;
      }
      if (/^##\s+/.test(line)) {
        out.push(`<h2>${inline(line.replace(/^##\s+/, ''))}</h2>`);
        i++; continue;
      }
      if (/^#\s+/.test(line)) {
        out.push(`<h1>${inline(line.replace(/^#\s+/, ''))}</h1>`);
        i++; continue;
      }

      // Unordered list
      if (/^\s*[-*]\s+/.test(line)) {
        const items: string[] = [];
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
          items.push(`<li>${inline(lines[i].replace(/^\s*[-*]\s+/, ''))}</li>`);
          i++;
        }
        out.push(`<ul>${items.join('')}</ul>`);
        continue;
      }

      // Ordered list
      if (/^\s*\d+\.\s+/.test(line)) {
        const items: string[] = [];
        while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
          items.push(`<li>${inline(lines[i].replace(/^\s*\d+\.\s+/, ''))}</li>`);
          i++;
        }
        out.push(`<ol>${items.join('')}</ol>`);
        continue;
      }

      // Blank line => paragraph break
      if (line.trim() === '') { out.push(''); i++; continue; }

      // Paragraph: collect until blank line
      const para: string[] = [line];
      i++;
      while (i < lines.length && lines[i].trim() !== '') {
        para.push(lines[i]);
        i++;
      }
      // Join inline with <br> to preserve author-intended line breaks
      out.push(`<p>${inline(para.join('<br>'))}</p>`);
    }

    return out.join('\n');
  }

  $: selectedHtml = selectedNarrative?.content
    ? renderMarkdownSafe(selectedNarrative.content)
    : '';

  function updateSelection() {
    try {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);
      if (!renderEl || !renderEl.contains(range.commonAncestorContainer)) return;
      const text = sel.toString().trim();
      selectedExcerpt = text || '';
    } catch {}
  }

  // Use document-level selectionchange to avoid mouse/keyboard handlers on non-interactive elements
  onMount(() => {
    const handler = () => updateSelection();
    document.addEventListener('selectionchange', handler);
    return () => { document.removeEventListener('selectionchange', handler); };
  });

  function clearSelection() {
    selectedExcerpt = '';
    const sel = window.getSelection();
    if (sel) sel.removeAllRanges();
  }

  function gotoVersion(delta: number) {
    if (!thread || !thread.files || thread.files.length === 0) return;
    const next = thread.index + delta;
    if (next < 0 || next >= thread.files.length) return;
    const fname = thread.files[next];
    getNarrativeContent(fname);
  }
</script>

<div class="drawer-overlay" class:is-open={isOpen} role="button" tabindex="0" on:click={onClose} on:keydown={(e) => (e.key==='Enter'||e.key===' ') && onClose()}></div>
<div class="drawer" class:is-open={isOpen}>
  <div class="drawer-content">
    <div class="drawer-header">
      <h2>Narratives</h2>
      <button on:click={onClose}>Close</button>
    </div>
    <div class="drawer-body">
      <div class="narrative-list">
        {#each narratives as narrative}
          <div class="narrative-item" role="button" tabindex="0" on:click={() => getNarrativeContent(narrative.filename)} on:keydown={(e) => (e.key==='Enter'||e.key===' ') && getNarrativeContent(narrative.filename)}>
            {narrative.filename}
          </div>
        {/each}
      </div>
      <div class="narrative-content">
        {#if selectedNarrative}
          <div class="content-header">
            <h3 class="filename">{selectedNarrative.filename}</h3>
            <div class="toolbar">
              <button class="btn" title="Previous version" on:click={() => gotoVersion(-1)} disabled={thread.index <= 0}>◀</button>
              <span class="ver">v {thread.index + 1}/{Math.max(thread.files.length, 1)}</span>
              <button class="btn" title="Next version" on:click={() => gotoVersion(1)} disabled={thread.index >= thread.files.length - 1}>▶</button>
              <button class="btn primary" on:click={() => (isIterateOpen = true)}>Iterate</button>
              <button class="btn" on:click={() => (isIterateOpen = true)} disabled={!selectedExcerpt}>Iterate Selection</button>
              <button class="btn danger" on:click={() => deleteNarrative(selectedNarrative!.filename)}>Delete</button>
            </div>
          </div>
          {#if selectedExcerpt}
            <div class="selection-chip">
              Focused selection: <span class="excerpt">{selectedExcerpt.slice(0, 140)}{selectedExcerpt.length > 140 ? '…' : ''}</span>
              <button class="link" on:click={clearSelection}>Clear</button>
            </div>
          {/if}
          <div class="narrative-render" role="region" aria-label="Narrative content" bind:this={renderEl}>
            {@html selectedHtml}
          </div>
        {:else}
          <p>Select a narrative to view its content.</p>
        {/if}
      </div>
    </div>
  </div>
</div>

<NarrativeIterateModal
  open={isIterateOpen}
  currentContent={selectedNarrative?.content || ''}
  parentFilename={selectedNarrative?.filename || ''}
  selectedExcerpt={selectedExcerpt}
  on:close={() => (isIterateOpen = false)}
  on:done={async (e) => {
    isIterateOpen = false;
    await getNarratives();
    const fname = e.detail?.filename;
    if (fname) await getNarrativeContent(fname);
  }}
/>

<style>
  .drawer {
    position: fixed;
    top: 0;
    right: -500px; /* Start off-screen */
    width: 500px;
    height: 100%;
    background-color: white;
    box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
    transition: right 0.3s ease-in-out;
    z-index: 1000;
  }

  .drawer.is-open {
    right: 0; /* Slide in */
  }

  .drawer-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 999;
    display: none; /* shown when drawer is open */
  }
  .drawer-overlay.is-open { display: block; }

  .drawer-content {
    padding: 1rem;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
  }

  .drawer-body {
    display: flex;
    flex-grow: 1;
    overflow: hidden;
  }

  .narrative-list {
    width: 150px;
    border-right: 1px solid #ccc;
    padding-right: 1rem;
    overflow-y: auto;
  }

  .narrative-item {
    padding: 0.5rem;
    cursor: pointer;
  }

  .narrative-item:hover {
    background-color: #f0f0f0;
  }

  .narrative-content {
    flex-grow: 1;
    padding-left: 1rem;
    overflow-y: auto;
  }

  .narrative-render {
    color: #111;
    line-height: 1.5;
  }
  :global(.narrative-render h1),
  :global(.narrative-render h2),
  :global(.narrative-render h3) { margin: 0.5rem 0; }
  :global(.narrative-render p) { margin: 0.5rem 0; }
  :global(.narrative-render ul) { margin: 0.5rem 1.25rem; padding-left: 1rem; }
  :global(.narrative-render li) { margin: 0.25rem 0; }

  .content-header { position: sticky; top: 0; background: #fff; padding-bottom: .5rem; margin-bottom: .5rem; z-index: 1; }
  .content-header .filename { display: inline-block; margin: 0 .75rem .25rem 0; }
  .toolbar { display: inline-flex; gap: .5rem; flex-wrap: wrap; vertical-align: middle; }
  /* removed unused .actions */
  .btn { border: none; padding: .4rem .7rem; border-radius: 6px; cursor: pointer; background: #e5e7eb; }
  .btn.primary { background: #3B82F6; color: white; }
  .btn.danger { background: #ef4444; color: #fff; }
  .btn[disabled] { opacity: .6; cursor: not-allowed; }
  .selection-chip { background: #f1f5f9; border: 1px solid #e2e8f0; padding: .35rem .5rem; border-radius: 6px; margin: 0 0 .5rem 0; font-size: .9rem; color: #334155; display: inline-flex; gap: .5rem; align-items: baseline; }
  .selection-chip .excerpt { font-style: italic; }
  .selection-chip .link { border: none; padding: 0; margin: 0; background: none; color: #2563eb; cursor: pointer; }
</style>
