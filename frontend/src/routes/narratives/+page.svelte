<script lang="ts">
  import { onMount } from 'svelte';
  import { BACKEND_URL } from '$lib/config';
  import NarrativeIterateModal from '$lib/components/NarrativeIterateModal.svelte';
  import NarrativesFiltersBar from '$lib/components/NarrativesFiltersBar.svelte';
  import NarrativesBulkActions from '$lib/components/NarrativesBulkActions.svelte';

  type Narrative = { filename: string; content?: string; title?: string };

  let narratives: Narrative[] = $state([]);
  let selectedNarrative: Narrative | null = $state(null);
  let thread: { files: string[]; index: number } = $state({ files: [], index: 0 });
  let isIterateOpen = $state(false);
  let isGenerating = $state(false);
  let selectedExcerpt = $state('');
  let renderEl = $state<HTMLDivElement | null>(null);
  let layoutEl: HTMLDivElement | null = null;

  // Resizable sidebar
  let sidebarWidth = $state<number>(280);
  let resizing = $state(false);
  onMount(() => {
    try {
      const v = localStorage.getItem('nh_narratives_sidebar_px');
      if (v) sidebarWidth = Math.max(180, Math.min(600, parseInt(v, 10) || 280));
    } catch {}
  });
  $effect(() => { try { localStorage.setItem('nh_narratives_sidebar_px', String(sidebarWidth)); } catch {} });
  function startResize(e: PointerEvent) {
    if (!layoutEl) return;
    resizing = true;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    const rect = layoutEl.getBoundingClientRect();
    const onMove = (ev: PointerEvent) => {
      const x = ev.clientX - rect.left;
      sidebarWidth = Math.max(180, Math.min(600, x));
      ev.preventDefault();
    };
    const onUp = (ev: PointerEvent) => {
      resizing = false;
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  }
  function resetResize() { sidebarWidth = 280; }

  let nfilters = $state<{ search: string; folder: string }>({ search: '', folder: '__ALL__' });

  async function loadList() {
    try {
      let ok = false;
      try {
        const r = await fetch(`${BACKEND_URL}/api/narratives/list`);
        if (r.ok) {
          const list: any[] = await r.json();
          narratives = list.map((x) => ({ filename: x.filename, title: x.title, folder: x.folder }));
          ok = true;
        }
      } catch {}
      if (!ok) {
        // Fallback to simple filenames list
        try {
          const r2 = await fetch(`${BACKEND_URL}/api/narratives`);
          if (r2.ok) {
            const files: string[] = await r2.json();
            narratives = files.map((f) => ({ filename: f }));
          }
        } catch {}
      }
    } catch {}
  }

  async function loadOne(filename: string) {
    try {
      const r = await fetch(`${BACKEND_URL}/api/narratives/${filename}`);
      if (r.ok) {
        const data = await r.json();
        selectedNarrative = { filename, content: data.content, title: (data as any).title };
        // thread
        try {
          const tr = await fetch(`${BACKEND_URL}/api/narratives/thread/${filename}`);
          thread = tr.ok ? await tr.json() : { files: [filename], index: 0 };
        } catch { thread = { files: [filename], index: 0 }; }
      }
    } catch {}
  }

  async function delOne(filename: string) {
    if (!confirm('Delete this narrative?')) return;
    try {
      const r = await fetch(`${BACKEND_URL}/api/narratives/${filename}`, { method: 'DELETE' });
      if (r.ok) { selectedNarrative = null; await loadList(); }
    } catch {}
  }

  function gotoVersion(delta: number) {
    if (!thread.files?.length) return;
    const next = thread.index + delta;
    if (next < 0 || next >= thread.files.length) return;
    loadOne(thread.files[next]);
  }

  // Multi-select with Shift/Ctrl on the sidebar list
  let selectedSet: Set<string> = $state(new Set());
  let lastSelectedIndex: number | null = $state(null);
  function isSelected(name: string): boolean { return selectedSet.has(name); }
  function clearSelection() { selectedSet = new Set(); lastSelectedIndex = null; }
  function handleItemClick(idx: number, e: MouseEvent) {
    const fname = filteredNarratives[idx]?.filename;
    if (!fname) return;
    const shift = e.shiftKey === true;
    const meta = e.ctrlKey === true || e.metaKey === true;
    if (shift && lastSelectedIndex != null) {
      const start = Math.min(lastSelectedIndex, idx);
      const end = Math.max(lastSelectedIndex, idx);
      const ns = new Set(selectedSet);
      for (let i = start; i <= end; i++) ns.add(filteredNarratives[i].filename);
      selectedSet = ns;
      loadOne(fname);
    } else if (meta) {
      const ns = new Set(selectedSet);
      if (ns.has(fname)) ns.delete(fname); else ns.add(fname);
      selectedSet = ns;
      lastSelectedIndex = idx;
      // do not change the viewer on pure toggle
    } else {
      selectedSet = new Set([fname]);
      lastSelectedIndex = idx;
      loadOne(fname);
    }
  }

  // Derived filtered narratives
  const folders = $derived((() => {
    const set = new Set<string>();
    for (const n of narratives) { const f = (n as any).folder || ''; if (f) set.add(f); }
    return Array.from(set).sort((a,b)=>a.localeCompare(b));
  })());
  const filteredNarratives = $derived((() => {
    const q = nfilters.search.trim().toLowerCase();
    return narratives.filter((n:any) => {
      if (nfilters.folder === '__UNFILED__') { if ((n.folder||'').trim() !== '') return false; }
      else if (nfilters.folder !== '__ALL__') { if ((n.folder||'').trim() !== nfilters.folder) return false; }
      if (!q) return true;
      const hay = `${n.title||''} ${n.filename}`.toLowerCase();
      return hay.includes(q);
    });
  })());

  async function moveSelectedTo(folder: string) {
    const names = Array.from(selectedSet);
    for (const fn of names) {
      try {
        await fetch(`${BACKEND_URL}/api/narratives/${fn}/folder`, {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ folder })
        });
      } catch {}
    }
    await loadList();
  }

  // Bulk actions
  let moveInput = $state('');
  async function deleteSelected() {
    if (!selectedSet.size) return;
    if (!confirm(`Delete ${selectedSet.size} selected narrative(s)?`)) return;
    const names = Array.from(selectedSet);
    for (const fn of names) {
      try { await fetch(`${BACKEND_URL}/api/narratives/${fn}`, { method: 'DELETE' }); } catch {}
    }
    clearSelection();
    await loadList();
    selectedNarrative = null;
  }
  async function combineSelected() {
    const names = Array.from(selectedSet);
    if (names.length < 2) return;
    try {
      const body = names.map((f) => ({ filename: f }));
      const r = await fetch(`${BACKEND_URL}/api/narratives`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (r.ok) {
        const data = await r.json();
        await loadList();
        if (data.filename) await loadOne(data.filename);
      }
    } catch {}
  }

  // Safe markdown render (copied from drawer)
  function escapeHtml(s: string): string { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function renderMarkdownSafe(text: string): string {
    if (!text) return '';
    let t = text.replace(/\\n/g,'\n').replace(/\r\n/g,'\n');
    t = escapeHtml(t);
    const inline = (s: string) => {
      s = s.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/__([^_]+)__/g,'<strong>$1</strong>');
      s = s.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g,'$1<em>$2</em>').replace(/(^|[^_])_([^_]+)_(?!_)/g,'$1<em>$2</em>');
      return s;
    };
    const lines = t.split(/\n/); const out: string[] = []; let i=0;
    while (i<lines.length) {
      const line = lines[i];
      if (/^###\s+/.test(line)) { out.push(`<h3>${inline(line.replace(/^###\s+/,''))}</h3>`); i++; continue; }
      if (/^##\s+/.test(line)) { out.push(`<h2>${inline(line.replace(/^##\s+/,''))}</h2>`); i++; continue; }
      if (/^#\s+/.test(line)) { out.push(`<h1>${inline(line.replace(/^#\s+/,''))}</h1>`); i++; continue; }
      if (/^\s*[-*]\s+/.test(line)) { const items: string[] = []; while (i<lines.length && /^\s*[-*]\s+/.test(lines[i])) { items.push(`<li>${inline(lines[i].replace(/^\s*[-*]\s+/,''))}</li>`); i++; } out.push(`<ul>${items.join('')}</ul>`); continue; }
      if (/^\s*\d+\.\s+/.test(line)) { const items: string[] = []; while (i<lines.length && /^\s*\d+\.\s+/.test(lines[i])) { items.push(`<li>${inline(lines[i].replace(/^\s*\d+\.\s+/,''))}</li>`); i++; } out.push(`<ol>${items.join('')}</ol>`); continue; }
      if (line.trim()==='') { out.push(''); i++; continue; }
      const para: string[] = [line]; i++; while (i<lines.length && lines[i].trim()!=='') { para.push(lines[i]); i++; }
      out.push(`<p>${inline(para.join('<br>'))}</p>`);
    }
    return out.join('\n');
  }

  const selectedHtml = $derived(selectedNarrative?.content ? renderMarkdownSafe(selectedNarrative.content) : '');

  function updateSelection() {
    try { const sel = window.getSelection(); if (!sel || sel.rangeCount===0) return; const range = sel.getRangeAt(0); if (!renderEl || !renderEl.contains(range.commonAncestorContainer)) return; const text = sel.toString().trim(); selectedExcerpt = text || ''; } catch {}
  }
  onMount(() => {
    loadList().then(() => {
      try {
        const params = new URLSearchParams(location.search);
        const open = params.get('open');
        if (open) loadOne(open);
      } catch {}
    });
    const handler = () => updateSelection();
    document.addEventListener('selectionchange', handler);
    return () => document.removeEventListener('selectionchange', handler);
  });
</script>

<main class="page">
  <header class="head">
    <NarrativesFiltersBar
      bind:filters={nfilters}
      folders={folders}
      counts={{ total: narratives.length, filtered: filteredNarratives.length }}
      on:selectAll={() => { selectedSet = new Set(filteredNarratives.map((n:any)=>n.filename)); }}
      on:clearSelection={() => { clearSelection(); }}
    />
  </header>
  <section class="layout" bind:this={layoutEl} style={`grid-template-columns: ${sidebarWidth}px 6px 1fr;`} class:resizing={resizing}>
    <aside class="list">
      {#each filteredNarratives as n, i}
        <button
          class="item"
          class:selected={isSelected(n.filename)}
          onclick={(e) => handleItemClick(i, e as MouseEvent)}
        >{n.title || n.filename}{#if (n as any).folder} <small class="chip">{(n as any).folder}</small>{/if}</button>
      {/each}
      {#if !narratives.length}
        <div class="empty">No narratives yet.</div>
      {/if}
    </aside>
    <div class="resizer" role="separator" aria-orientation="vertical" tabindex="-1" onpointerdown={startResize} ondblclick={resetResize} title="Drag to resize"></div>
    <article class="viewer">
      {#if selectedNarrative}
        <div class="toolbar">
          <h2 class="title">{selectedNarrative.title || selectedNarrative.filename}</h2>
          <div class="actions">
            <button class="btn" title="Previous" onclick={() => gotoVersion(-1)} disabled={thread.index<=0 || isGenerating}>◀</button>
            <span class="ver">v {thread.index + 1}/{Math.max(thread.files.length, 1)}</span>
            <button class="btn" title="Next" onclick={() => gotoVersion(1)} disabled={thread.index>=thread.files.length-1 || isGenerating}>▶</button>
            <button class="btn primary" onclick={() => (isIterateOpen = true)} disabled={isGenerating}>Iterate</button>
            <button class="btn" onclick={() => (isIterateOpen = true)} disabled={!selectedExcerpt || isGenerating}>Iterate Selection</button>
            <button class="btn danger" onclick={() => delOne(selectedNarrative!.filename)} disabled={isGenerating}>Delete</button>
            {#if isGenerating}<span class="loading">Generating…</span>{/if}
          </div>
        </div>
        {#if selectedExcerpt}
          <div class="selection">Selected: <em>{selectedExcerpt.slice(0,140)}{selectedExcerpt.length>140?'…':''}</em></div>
        {/if}
        <div class="content" bind:this={renderEl} aria-label="Narrative content" role="region">
          {@html selectedHtml}
        </div>
        <!-- floating bulk actions bar -->
        <NarrativesBulkActions
          selectedCount={selectedSet.size}
          isGenerating={isGenerating}
          folders={folders}
          on:selectAll={() => { selectedSet = new Set(filteredNarratives.map((n:any)=>n.filename)); }}
          on:clearSelection={() => { clearSelection(); }}
          on:bulkMove={(e) => moveSelectedTo((e.detail?.folder||''))}
          on:combineSelected={combineSelected}
          on:iterateSelected={() => (isIterateOpen = true)}
          on:deleteSelected={deleteSelected}
        />
      {:else}
        <div class="placeholder">Select a narrative on the left</div>
      {/if}
    </article>
  </section>

  <NarrativeIterateModal
    open={isIterateOpen}
    currentContent={selectedNarrative?.content || ''}
    parentFilename={selectedNarrative?.filename || ''}
    selectedExcerpt={selectedExcerpt}
    selectedNarratives={Array.from(selectedSet)}
    on:close={() => (isIterateOpen = false)}
    on:start={() => { isGenerating = true; }}
    on:finish={() => { isGenerating = false; }}
    on:done={async (e) => { isIterateOpen=false; isGenerating=false; await loadList(); const fname = e.detail?.filename; if (fname) await loadOne(fname); }}
  />
</main>

<style>
  .page { padding: 1rem; }
  .head { margin-bottom: .5rem; }
  .layout { display: grid; grid-template-columns: 240px 1fr; gap: 0; min-height: calc(100vh - 100px); position: relative; }
  .layout.resizing { cursor: col-resize; }
  .list { border-right: 1px solid #e5e7eb; padding: 0 .5rem 0 0; overflow:auto; }
  .resizer { width: 6px; cursor: col-resize; background: transparent; position: relative; }
  .resizer::after { content:''; position:absolute; left:2px; top:0; bottom:0; width:2px; background:#e5e7eb; }
  .item { display:block; width:100%; text-align:left; background:#f8fafc; border:1px solid #e5e7eb; border-radius:6px; padding:.4rem .6rem; margin-bottom:.4rem; cursor:pointer; }
  .item.selected { background:#eef2ff; border-color:#c7d2fe; }
  .empty { color:#6b7280; font-size:.9rem; }
  .viewer { overflow:auto; }
  .toolbar { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; margin-bottom:.5rem; }
  .title { margin:0 .5rem 0 0; }
  .actions { display:inline-flex; align-items:center; gap:.5rem; }
  .btn { border:none; background:#e5e7eb; padding:.35rem .6rem; border-radius:6px; cursor:pointer; }
  .btn.primary { background:#3B82F6; color:#fff; }
  .btn.danger { background:#ef4444; color:#fff; }
  .btn[disabled] { opacity:.6; cursor:not-allowed; }
  .ver { color:#374151; }
  .loading { color:#374151; font-style: italic; }
  .selection { background:#f1f5f9; border:1px solid #e2e8f0; padding:.35rem .5rem; border-radius:6px; margin-bottom:.5rem; }
  .content { color:#111; line-height:1.5; }
  .content :global(h1) { margin:.5rem 0; }
  .content :global(h2) { margin:.5rem 0; }
  .content :global(h3) { margin:.5rem 0; }
  .content :global(p) { margin:.5rem 0; }
  .content :global(ul) { margin:.5rem 1.25rem; padding-left:1rem; }
  .content :global(li) { margin:.25rem 0; }
  .chip { background:#e8f0fe; color:#1a73e8; border-radius:9999px; padding:0 .35rem; font-size:.75rem; }
  .folder-input { flex:0 0 220px; border:1px solid #e5e7eb; border-radius:6px; padding:.3rem .5rem; }
</style>
