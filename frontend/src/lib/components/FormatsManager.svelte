<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { BACKEND_URL } from '../config';
  import Modal from '$lib/components/common/Modal.svelte';

  export let open: boolean = false;

  type Format = { id: string; title: string; prompt: string };
  let formats: Format[] = [];
  let title = '';
  let prompt = '';
  let loading = false;
  let query = '';
  const dispatch = createEventDispatcher();

  async function load() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/formats`);
      if (res.ok) formats = await res.json();
    } catch {}
  }
  onMount(() => { if (open) load(); });
  let _wasOpen = false;
  $: if (open !== _wasOpen) {
    _wasOpen = open;
    if (open) load();
  }

  function closeOnEsc(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }

  async function save() {
    if (!title.trim() || !prompt.trim()) return;
    loading = true;
    try {
      const res = await fetch(`${BACKEND_URL}/api/formats`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), prompt: prompt.trim() })
      });
      if (res.ok) {
        title = ''; prompt = '';
        await load();
      }
    } finally { loading = false; }
  }

  async function remove(id: string) {
    if (!confirm('Delete this format?')) return;
    await fetch(`${BACKEND_URL}/api/formats/${id}`, { method: 'DELETE' });
    await load();
  }

  function close() { dispatch('close'); }

  function copyText(text: string) {
    try { navigator.clipboard.writeText(text); } catch {}
  }

  // Inline edit support
  let editId: string | null = null;
  let editTitle = '';
  let editPrompt = '';
  function startEdit(f: Format) {
    editId = f.id; editTitle = f.title; editPrompt = f.prompt;
  }
  function cancelEdit() { editId = null; editTitle = ''; editPrompt = ''; }
  async function saveEdit() {
    if (!editId || !editTitle.trim() || !editPrompt.trim()) return;
    loading = true;
    try {
      const res = await fetch(`${BACKEND_URL}/api/formats`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: editId, title: editTitle.trim(), prompt: editPrompt.trim() })
      });
      if (res.ok) { await load(); cancelEdit(); }
    } finally { loading = false; }
  }

  async function duplicateFormat(f: Format) {
    loading = true;
    try {
      await fetch(`${BACKEND_URL}/api/formats`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: `${f.title} (copy)`, prompt: f.prompt })
      });
      await load();
    } finally { loading = false; }
  }

  // Expand/collapse per row (compact by default)
  let expanded: Record<string, boolean> = {};
  function toggleExpand(id: string) { expanded = { ...expanded, [id]: !expanded[id] }; }
  function preview(text: string, max = 100) {
    const t = (text || '').replace(/\s+/g, ' ').trim();
    return t.length > max ? t.slice(0, max - 1) + '…' : t;
  }
</script>

{#if open}
  <Modal {open} title="Formats" on:close={close}>
    <div class="modal-body">
      <div class="toolbar">
        <input class="search" placeholder="Search formats…" bind:value={query} />
      </div>
      <div class="new">
        <input placeholder="Title" bind:value={title} />
        <textarea placeholder="Prompt (task format)" bind:value={prompt}></textarea>
        <div class="row-actions">
          <button class="primary" on:click={save} disabled={loading || !title.trim() || !prompt.trim()}>Add Format</button>
          <button class="ghost" on:click={()=>{title=''; prompt='';}}>Clear</button>
        </div>
      </div>
      <div class="list">
        {#each formats.filter(f => f.title.toLowerCase().includes(query.toLowerCase()) || f.prompt.toLowerCase().includes(query.toLowerCase())) as f (f.id)}
          <div class="row" class:open={!!expanded[f.id]}>
            {#if editId === f.id}
              <div class="meta">
                <input placeholder="Title" bind:value={editTitle} />
                <textarea bind:value={editPrompt}></textarea>
              </div>
              <div class="actions">
                <button class="primary small" disabled={loading || !editTitle.trim() || !editPrompt.trim()} on:click={saveEdit}>Save</button>
                <button class="ghost small" on:click={cancelEdit}>Cancel</button>
              </div>
            {:else}
              <button type="button" class="toggle" aria-label="Toggle" aria-expanded={!!expanded[f.id]} on:click={() => toggleExpand(f.id)}>{expanded[f.id] ? '▾' : '▸'}</button>
              <div class="meta compact" on:click={() => toggleExpand(f.id)} role="button" aria-label="Toggle format" tabindex="0" on:keydown={(e)=>{ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); toggleExpand(f.id); } }}>
                <div class="t">{f.title}</div>
                {#if !expanded[f.id]}
                  <div class="preview">{preview(f.prompt)}</div>
                {/if}
                {#if expanded[f.id]}
                  <pre class="p">{f.prompt}</pre>
                {/if}
              </div>
              <div class="actions">
                <button class="ghost small" title="Copy" on:click={() => copyText(f.prompt)}>Copy</button>
                <button class="ghost small" title="Duplicate" on:click={() => duplicateFormat(f)}>Duplicate</button>
                <button class="ghost small" title="Edit" on:click={() => startEdit(f)}>Edit</button>
                <button class="danger small" on:click={() => remove(f.id)}>Delete</button>
              </div>
            {/if}
          </div>
        {/each}
        {#if !formats.length}
          <div class="empty">No formats yet. Add one above.</div>
        {/if}
      </div>
    </div>
  </Modal>
{/if}

<style>
  /* Uses common Modal */
  .toolbar { display:flex; justify-content:flex-end; margin-bottom:.5rem; }
  .search { width: 260px; max-width: 100%; border:1px solid #e5e7eb; border-radius:6px; padding:.4rem .6rem; }
  .modal-body { overflow: auto; min-height: 0; }
  .new { display:flex; flex-direction: column; gap:.5rem; margin-bottom: 1rem; }
  input, textarea { padding:.5rem; border:1px solid #e5e7eb; border-radius:6px; width:100%; }
  textarea { min-height: 120px; resize: vertical; }
  .list { display:flex; flex-direction: column; gap:.5rem; }
  .row { display:grid; grid-template-columns: auto 1fr auto; gap:.5rem; align-items:flex-start; border:1px solid #e5e7eb; border-radius:6px; padding:.4rem .5rem; }
  .row .toggle { border:none; background:#f3f4f6; border-radius:6px; width:26px; height:26px; cursor:pointer; }
  .row.open .toggle { background:#eef2ff; color:#4338ca; }
  .meta { flex:1; }
  .meta.compact .t { font-weight:600; margin:0; font-size:.95rem; }
  .preview { color:#6b7280; font-size:.85rem; margin-top:.15rem; }
  .t { font-weight:600; margin-bottom:.25rem; }
  .p { margin:0; white-space: pre-wrap; background:#f8fafc; padding:.5rem; border-radius:6px; }
  .row-actions { display:flex; gap:.5rem; }
  .actions { display:flex; align-items:center; gap:.35rem; }
  .primary { background:#3B82F6; color:#fff; border:none; padding:.45rem .75rem; border-radius:6px; cursor:pointer; align-self:flex-start; }
  .danger { background:#ef4444; color:#fff; border:none; padding:.35rem .6rem; border-radius:6px; cursor:pointer; }
  .ghost { background:#f3f4f6; color:#111; border:1px solid #e5e7eb; padding:.35rem .6rem; border-radius:6px; cursor:pointer; }
  .small { font-size:.85rem; padding:.3rem .5rem; }
  .empty { color:#6b7280; }
  h3 { margin:0; }
  pre { overflow:auto; }
  @media (max-width: 640px){ .row { flex-direction: column; } }
</style>
