<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let name: string;
  export let count: number = 0;
  export let layout: 'full' | 'compact' = 'full';

  const dispatch = createEventDispatcher();
  let isOver = false;

  function onDragOver(e: DragEvent) {
    // Allow drop when payload contains our custom type
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
      if (!raw) return;
      const data = JSON.parse(raw || '{}');
      const filenames: string[] = Array.isArray(data.filenames) ? data.filenames : [];
      if (!filenames.length) return;
      dispatch('moveToFolder', { folder: name, filenames });
    } catch (err) {
      console.error('Drop parse failed', err);
    }
  }
</script>

<li class="card {layout}" class:over={isOver} on:dragover={onDragOver} on:dragleave={onDragLeave} on:drop={onDrop} tabindex="0">
  <div class="header">
    <p class="title">{name}</p>
    <small class="meta">{count} {count === 1 ? 'note' : 'notes'}</small>
  </div>
  <div class="folder-body">
    <p>Drop selected notes here to move them.</p>
  </div>
</li>

<style>
  .card { position: relative; margin-bottom: 1.5rem; padding: 1rem; background-color: #fdfcfb; border-radius: 8px; cursor: default; outline: 2px solid #e5e7eb; transition: outline-color 120ms ease, box-shadow 120ms ease; }
  .card.compact { margin-bottom: .75rem; padding: .6rem .7rem; }
  .card.over { outline-color: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.15); }
  .header { display:flex; justify-content: space-between; align-items: baseline; gap: .5rem; flex-wrap: wrap; }
  .title { margin:0; font-weight: 700; font-size: 1rem; color:#111; }
  .card.compact .title { font-size: .95rem; }
  .meta { color:#666; }
  .folder-body { background:#fff; border-left:5px solid #c7d2fe; border-radius:4px; padding:.75rem 1rem; color:#4b5563; }
</style>

