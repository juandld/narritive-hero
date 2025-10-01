<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let name: string;
  export let count: number = 0;
  export let layout: 'full' | 'compact' = 'full';

  const dispatch = createEventDispatcher();
  let isOver = false;
  let overCount = 0;

  function onDragOver(e: DragEvent) {
    // Allow drop when payload contains our custom type
    if (e.dataTransfer) {
      const types = Array.from(e.dataTransfer.types || []);
      if (types.includes('application/json')) {
        e.preventDefault();
        isOver = true;
        try {
          const sel: any = (window as any).__selectedNotes;
          overCount = sel && typeof sel.size === 'number' ? sel.size : 1;
        } catch { overCount = 1; }
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

<li class="card {layout}" class:over={isOver} on:dragover={onDragOver} on:dragleave={onDragLeave} on:drop={onDrop} tabindex="0" role="button" on:click={() => dispatch('open', { name })} on:keydown={(e)=>{ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); dispatch('open', { name }); } }}>
  <div class="header">
    <p class="title">{name}</p>
    <div class="right">
      <small class="meta">{count} {count === 1 ? 'note' : 'notes'}</small>
      <button class="del" title="Delete folder" aria-label="Delete folder" on:click|stopPropagation={() => dispatch('delete', { name })}>×</button>
    </div>
  </div>
  <div class="folder-body">
    <p>Drop selected notes here to move them.</p>
    {#if isOver}
      <div class="overlay">Move {overCount} here</div>
    {/if}
  </div>
</li>

<style>
  .card { position: relative; margin-bottom: 1.5rem; padding: 1rem; background-color: #fdfcfb; border-radius: 8px; cursor: default; outline: 2px solid #e5e7eb; transition: outline-color 120ms ease, box-shadow 120ms ease; }
  .card.compact { margin-bottom: .75rem; padding: .6rem .7rem; }
  .card.over { outline-color: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.15); }
  .header { display:flex; justify-content: space-between; align-items: baseline; gap: .5rem; flex-wrap: wrap; }
  .title { margin:0; font-weight: 700; font-size: 1rem; color:#111; }
  .card.compact .title { font-size: .95rem; }
  .right { display:flex; align-items:center; gap:.35rem; }
  .meta { color:#666; }
  .del { background:#fee2e2; border:1px solid #fecaca; color:#991b1b; width:24px; height:24px; border-radius:6px; cursor:pointer; }
  .folder-body { background:#fff; border-left:5px solid #c7d2fe; border-radius:4px; padding:.75rem 1rem; color:#4b5563; }
  .overlay { margin-top:.5rem; display:inline-block; background:#10B981; color:#fff; border-radius:9999px; padding:.15rem .5rem; font-size:.8rem; }
</style>
