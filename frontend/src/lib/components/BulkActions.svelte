<script lang="ts">
  // Floating bottom action bar for selected notes
  import { createEventDispatcher } from 'svelte';

  export let selectedCount = 0;
  export let isDeleting = false;

  const dispatch = createEventDispatcher();
  function onDelete() { dispatch('deleteSelected'); }
  function onCreate() { dispatch('createNarrative'); }
  function onSelectAll() { dispatch('selectAll'); }
  function onClear() { dispatch('clearSelection'); }
</script>

{#if selectedCount > 0}
  <div class="bulk-actions">
    <div class="left">
      <button class="pill" on:click={onSelectAll} title="Select all">Select all</button>
      <button class="pill" on:click={onClear} title="Clear selection">Clear</button>
    </div>
    <button class="action-button delete" disabled={isDeleting} on:click={onDelete}>
      {isDeleting ? 'Deleting…' : `Delete ${selectedCount} selected`}
    </button>
    <button class="action-button create" on:click={onCreate}>
      Create Narrative from {selectedCount} note(s)
    </button>
  </div>
{/if}

<style>
  .bulk-actions {
    position: fixed;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 1rem;
    align-items: center;
    z-index: 10;
  }
  .left { display:flex; gap:.5rem; }
  .pill { background:#fff; color:#111; border:1px solid #e5e7eb; padding:.5rem .8rem; border-radius: 9999px; cursor:pointer; }
  .action-button {
    border: none;
    padding: 1rem 1.5rem;
    border-radius: 50px;
    cursor: pointer;
    font-size: 1.1rem;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    color: white;
  }
  .action-button.create { background-color: #28a745; }
  .action-button.delete { background-color: #db4437; }
</style>
