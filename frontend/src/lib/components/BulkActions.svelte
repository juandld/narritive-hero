<script lang="ts">
  // Floating bottom action bar for selected notes
  import { createEventDispatcher } from 'svelte';

  export let selectedCount = 0;
  export let isDeleting = false;

  const dispatch = createEventDispatcher();
  function onDelete() { dispatch('deleteSelected'); }
  function onCreate() { dispatch('createNarrative'); }
</script>

{#if selectedCount > 0}
  <div class="bulk-actions">
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

