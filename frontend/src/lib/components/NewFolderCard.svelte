<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();
  let name = '';
  let isOver = false;

  function create() {
    const n = name.trim();
    if (!n) return;
    dispatch('create', { name: n });
    name = '';
  }

  function onDragOver(e: DragEvent) {
    if (e.dataTransfer) {
      const types = Array.from(e.dataTransfer.types || []);
      if (types.includes('application/json')) {
        e.preventDefault();
        isOver = true;
      }
    }
  }
  function onDragLeave() { isOver = false; }
  function onDrop(e: DragEvent) {
    e.preventDefault();
    isOver = false;
    try {
      const raw = e.dataTransfer?.getData('application/json');
      const data = raw ? JSON.parse(raw) : null;
      const filenames: string[] = data && Array.isArray(data.filenames) ? data.filenames : [];
      const n = name.trim();
      if (!n || !filenames.length) return;
      dispatch('createAndMove', { name: n, filenames });
      name = '';
    } catch {}
  }
</script>

<li class="card" class:over={isOver} on:dragover={onDragOver} on:dragleave={onDragLeave} on:drop={onDrop}>
  <div class="header">
    <p class="title">New Folder</p>
  </div>
  <div class="body">
    <input placeholder="Folder name" bind:value={name} on:keydown={(e)=>{ if(e.key==='Enter') create(); }} />
    <button on:click={create}>Create</button>
  </div>
  <small class="hint">Tip: type a name, then drop notes here to create and move.</small>
</li>

<style>
  .card { position: relative; margin-bottom: 1.5rem; padding: 1rem; background-color: #f9fafb; border-radius: 8px; outline: 2px dashed #e5e7eb; transition: outline-color 120ms ease, box-shadow 120ms ease; }
  .card.over { outline-color: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.15); }
  .header { display:flex; justify-content: space-between; align-items: baseline; gap: .5rem; flex-wrap: wrap; }
  .title { margin:0; font-weight: 700; font-size: 1rem; color:#111; }
  .body { display:flex; gap:.5rem; align-items:center; }
  input { flex:1; padding:.35rem .5rem; border:1px solid #e5e7eb; border-radius:6px; }
  button { padding:.35rem .6rem; border:1px solid #e5e7eb; background:#f3f4f6; border-radius:6px; cursor:pointer; }
  .hint { color:#6b7280; }
</style>

