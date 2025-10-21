<script lang="ts">
  // Floating bottom action bar for selected notes
  import { createEventDispatcher } from 'svelte';

  export let selectedCount = 0;
  export let isDeleting = false;
  export let folders: string[] = [];

  const dispatch = createEventDispatcher();
  function onDelete() { dispatch('deleteSelected'); }
  function onCreate() { dispatch('createNarrative'); }
  function onSelectAll() { dispatch('selectAll'); }
  function onClear() { dispatch('clearSelection'); }
  let showMenu = false;
  function toggleMoveMenu() { showMenu = !showMenu; }
  function chooseMoveTarget(val: string) {
    dispatch('bulkMove', { folder: val || '' });
    showMenu = false;
  }
</script>

{#if selectedCount > 0}
  <div class="bulk-actions">
    <div class="seg left">
      <button class="pill" on:click={onSelectAll} title="Select all">Select all</button>
      <button class="pill" on:click={onClear} title="Clear selection">Clear selection</button>
    </div>
    <div class="seg move" data-hasmenu={showMenu}>
      <button class="pill" on:click={toggleMoveMenu} aria-haspopup="menu" aria-expanded={showMenu} title="Move selected">Move…</button>
      {#if showMenu}
        <div class="menu-backdrop" role="button" aria-label="Close move menu" tabindex="0" on:click={() => (showMenu = false)} on:keydown={(e)=>{ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); showMenu=false; } }}></div>
        <div class="menu" role="menu">
          <button role="menuitem" class="menu-item" on:click={() => chooseMoveTarget('')}>Unfiled</button>
          {#each folders as f}
            <button role="menuitem" class="menu-item" on:click={() => chooseMoveTarget(f)}>{f}</button>
          {/each}
        </div>
      {/if}
    </div>
    <div class="seg right">
      <button class="btn delete" disabled={isDeleting} on:click={onDelete}>
        {isDeleting ? 'Deleting…' : `Delete (${selectedCount})`}
      </button>
      <button class="btn create" on:click={onCreate}>
        Create Narrative ({selectedCount})
      </button>
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
    z-index: 20;
  }
  .seg { display:flex; align-items:center; gap:.5rem; }
  .left, .move, .right { }
  .pill { background:#fff; color:#111; border:1px solid #e5e7eb; padding:.45rem .8rem; border-radius: 10px; cursor:pointer; }
  .move { position: relative; }
  .menu-backdrop { position: fixed; inset: 0; background: transparent; z-index: 19; }
  .menu { position: absolute; bottom: 120%; left: 0; background:#fff; border:1px solid #e5e7eb; border-radius:10px; box-shadow:0 8px 24px rgba(0,0,0,0.12); padding:.25rem; min-width: 160px; z-index: 21; }
  .menu-item { display:block; width:100%; text-align:left; background:#fff; border:none; padding:.45rem .6rem; border-radius:8px; cursor:pointer; }
  .menu-item:hover { background:#f3f4f6; }
  .btn { border:1px solid transparent; padding:.55rem .9rem; border-radius: 10px; cursor:pointer; color:#fff; }
  .btn.create { background-color: #28a745; }
  .btn.delete { background-color: #db4437; }
  /* .sr-only removed as unused */
</style>
