<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  export let selectedCount = 0;
  export let isGenerating = false;
  export let folders: string[] = [];

  const dispatch = createEventDispatcher();
  function onSelectAll(){ dispatch('selectAll'); }
  function onClear(){ dispatch('clearSelection'); }
  function onMove(folder: string){ dispatch('bulkMove', { folder }); }
  function onCombine(){ dispatch('combineSelected'); }
  function onIterate(){ dispatch('iterateSelected'); }
  function onDelete(){ dispatch('deleteSelected'); }

  let showMenu = false;
  function toggleMenu(){ showMenu = !showMenu; }
</script>

{#if selectedCount > 0}
  <div class="bulk-actions" role="region" aria-live="polite">
    <div class="seg left">
      <button class="pill" onclick={onSelectAll} title="Select all">Select all</button>
      <button class="pill" onclick={onClear} title="Clear selection">Clear selection</button>
    </div>
    <div class="seg move" data-hasmenu={showMenu}>
      <button class="pill" onclick={toggleMenu} aria-haspopup="menu" aria-expanded={showMenu} title="Move to folder">Move…</button>
      {#if showMenu}
        <div class="menu-backdrop" role="button" aria-label="Close move menu" tabindex="0" onclick={() => (showMenu = false)}></div>
        <div class="menu" role="menu">
          <button role="menuitem" class="menu-item" onclick={() => onMove('')}>Unfiled</button>
          {#each folders as f}
            <button role="menuitem" class="menu-item" onclick={() => onMove(f)}>{f}</button>
          {/each}
        </div>
      {/if}
    </div>
    <div class="seg right">
      <button class="btn" onclick={onCombine} disabled={selectedCount < 2 || isGenerating}>Combine</button>
      <button class="btn create" onclick={onIterate} disabled={isGenerating}>Iterate</button>
      <button class="btn delete" onclick={onDelete} disabled={isGenerating}>Delete</button>
    </div>
  </div>
{/if}

<style>
  .bulk-actions {
    position: fixed;
    left: 50%;
    bottom: 1rem;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 1rem;
    background: rgba(255,255,255,0.95);
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: .5rem .75rem;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    z-index: 1002;
  }
  .seg { display:flex; align-items:center; gap:.5rem; }
  .pill { background:#fff; color:#111; border:1px solid #e5e7eb; padding:.45rem .8rem; border-radius: 10px; cursor:pointer; }
  .move { position: relative; }
  .menu-backdrop { position: fixed; inset: 0; background: transparent; z-index: 1001; }
  .menu { position: absolute; bottom: 120%; left: 0; background:#fff; border:1px solid #e5e7eb; border-radius:10px; box-shadow:0 8px 24px rgba(0,0,0,0.12); padding:.25rem; min-width: 160px; z-index: 1003; }
  .menu-item { display:block; width:100%; text-align:left; background:#fff; border:none; padding:.45rem .6rem; border-radius:8px; cursor:pointer; }
  .menu-item:hover { background:#f3f4f6; }
  .btn { border:1px solid transparent; padding:.55rem .9rem; border-radius: 10px; cursor:pointer; color:#fff; background:#6b7280; }
  .btn.create { background-color: #28a745; }
  .btn.delete { background-color: #db4437; }
</style>

