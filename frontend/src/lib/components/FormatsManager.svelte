<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { BACKEND_URL } from '../config';

  export let open: boolean = false;

  type Format = { id: string; title: string; prompt: string };
  let formats: Format[] = [];
  let title = '';
  let prompt = '';
  let loading = false;
  const dispatch = createEventDispatcher();

  async function load() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/formats`);
      if (res.ok) formats = await res.json();
    } catch {}
  }
  onMount(() => { if (open) load(); });
  $: if (open) load();

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
</script>

{#if open}
  <div class="modal-overlay" role="button" tabindex="0" on:click={close} on:keydown={(e) => (e.key==='Enter'||e.key===' ') && close()}></div>
  <div class="modal" role="dialog" aria-modal="true">
    <div class="modal-header">
      <h3>Formats</h3>
      <button class="x" on:click={close}>×</button>
    </div>
    <div class="modal-body">
      <div class="new">
        <input placeholder="Title" bind:value={title} />
        <textarea placeholder="Prompt (task format)" bind:value={prompt}></textarea>
        <button class="primary" on:click={save} disabled={loading || !title.trim() || !prompt.trim()}>Save</button>
      </div>
      <div class="list">
        {#each formats as f}
          <div class="row">
            <div class="meta">
              <div class="t">{f.title}</div>
              <pre class="p">{f.prompt}</pre>
            </div>
            <button class="danger" on:click={() => remove(f.id)}>Delete</button>
          </div>
        {/each}
        {#if !formats.length}
          <div class="empty">No formats yet. Add one above.</div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 70; }
  .modal { position: fixed; top: 8vh; left: 50%; transform: translateX(-50%);
           background: #fff; padding: 1rem; border-radius: 8px; width: min(800px, 92vw); z-index: 71; box-shadow: 0 10px 30px rgba(0,0,0,.2); }
  .modal-header { display:flex; align-items:center; justify-content: space-between; margin-bottom:.5rem; }
  .x { background:none; border:none; font-size:1.2rem; cursor:pointer; }
  .new { display:flex; flex-direction: column; gap:.5rem; margin-bottom: 1rem; }
  input, textarea { padding:.5rem; border:1px solid #e5e7eb; border-radius:6px; width:100%; }
  textarea { min-height: 120px; resize: vertical; }
  .list { display:flex; flex-direction: column; gap:.5rem; }
  .row { display:flex; gap:.5rem; align-items:flex-start; border:1px solid #e5e7eb; border-radius:6px; padding:.5rem; }
  .meta { flex:1; }
  .t { font-weight:600; margin-bottom:.25rem; }
  .p { margin:0; white-space: pre-wrap; background:#f8fafc; padding:.5rem; border-radius:6px; }
  .primary { background:#3B82F6; color:#fff; border:none; padding:.5rem .9rem; border-radius:6px; cursor:pointer; align-self:flex-start; }
  .danger { background:#ef4444; color:#fff; border:none; padding:.4rem .7rem; border-radius:6px; cursor:pointer; }
  .empty { color:#6b7280; }
  h3 { margin:0; }
  pre { overflow:auto; }
  @media (max-width: 640px){ .row { flex-direction: column; } }
</style>

