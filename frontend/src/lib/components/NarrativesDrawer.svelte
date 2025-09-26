<script lang="ts">
  import { onMount } from 'svelte';

  type Narrative = {
    filename: string;
    content?: string;
  };

  export let isOpen: boolean;
  export let onClose: () => void;
  export let initialSelect: string | null = null;

  let narratives: Narrative[] = [];
  let selectedNarrative: Narrative | null = null;

  import { BACKEND_URL } from '../config';

  async function getNarratives() {
    try {
      const response = await fetch(`${BACKEND_URL}/api/narratives`);
      if (response.ok) {
        const filenames: string[] = await response.json();
        narratives = filenames.map((filename) => ({ filename }));
      } else {
        console.error('Failed to fetch narratives:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to fetch narratives:', error);
    }
  }

  async function getNarrativeContent(filename: string) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/narratives/${filename}`);
      if (response.ok) {
        const data = await response.json();
        selectedNarrative = { filename, content: data.content };
      } else {
        console.error('Failed to fetch narrative content:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to fetch narrative content:', error);
    }
  }

  async function deleteNarrative(filename: string) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/narratives/${filename}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        console.log('Delete successful');
        selectedNarrative = null;
        await getNarratives(); // Refresh the list
      } else {
        console.error('Delete failed');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
    }
  }

  onMount(() => {
    if (isOpen) {
      getNarratives();
    }
  });

  $: if (isOpen) {
    getNarratives();
  }

  // If parent provides an initial filename to select, fetch its content when open
  $: if (isOpen && initialSelect) {
    getNarrativeContent(initialSelect);
  }
</script>

<div class="drawer-overlay" class:is-open={isOpen} role="button" tabindex="0" on:click={onClose} on:keydown={(e) => (e.key==='Enter'||e.key===' ') && onClose()}></div>
<div class="drawer" class:is-open={isOpen}>
  <div class="drawer-content">
    <div class="drawer-header">
      <h2>Narratives</h2>
      <button on:click={onClose}>Close</button>
    </div>
    <div class="drawer-body">
      <div class="narrative-list">
        {#each narratives as narrative}
          <div class="narrative-item" role="button" tabindex="0" on:click={() => getNarrativeContent(narrative.filename)} on:keydown={(e) => (e.key==='Enter'||e.key===' ') && getNarrativeContent(narrative.filename)}>
            {narrative.filename}
          </div>
        {/each}
      </div>
      <div class="narrative-content">
        {#if selectedNarrative}
          <h3>{selectedNarrative.filename}</h3>
          <p>{selectedNarrative.content}</p>
          <button on:click={() => deleteNarrative(selectedNarrative!.filename)}>Delete</button>
        {:else}
          <p>Select a narrative to view its content.</p>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .drawer {
    position: fixed;
    top: 0;
    right: -500px; /* Start off-screen */
    width: 500px;
    height: 100%;
    background-color: white;
    box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
    transition: right 0.3s ease-in-out;
    z-index: 1000;
  }

  .drawer.is-open {
    right: 0; /* Slide in */
  }

  .drawer-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 999;
    display: none; /* shown when drawer is open */
  }
  .drawer-overlay.is-open { display: block; }

  .drawer-content {
    padding: 1rem;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
  }

  .drawer-body {
    display: flex;
    flex-grow: 1;
    overflow: hidden;
  }

  .narrative-list {
    width: 150px;
    border-right: 1px solid #ccc;
    padding-right: 1rem;
    overflow-y: auto;
  }

  .narrative-item {
    padding: 0.5rem;
    cursor: pointer;
  }

  .narrative-item:hover {
    background-color: #f0f0f0;
  }

  .narrative-content {
    flex-grow: 1;
    padding-left: 1rem;
    overflow-y: auto;
  }
</style>
