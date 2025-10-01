<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let folders: { name: string; count: number }[] = [];
  export let selected: string = '';
  export let unfiledCount: number = 0;

  const dispatch = createEventDispatcher();

  let newFolder = '';

  function select(name: string) {
    dispatch('select', name);
  }

  function createFolder() {
    const n = newFolder.trim();
    if (!n) return;
    dispatch('create', n);
    newFolder = '';
  }
</script>

<aside class="folders" aria-label="Folders">
  <div class="hdr">Folders</div>
  <button class="all {selected === '' ? 'active' : ''}" on:click={() => select('')}>All Notes</button>
  <button class="unfiled {selected === '__UNFILED__' ? 'active' : ''}" on:click={() => select('__UNFILED__')}>
    Unfiled <span class="count">{unfiledCount}</span>
  </button>
  <ul>
    {#each folders as f}
      <li>
        <button class={selected === f.name ? 'active' : ''} on:click={() => select(f.name)}>
          <span class="name">{f.name}</span>
          <span class="count">{f.count}</span>
        </button>
      </li>
    {/each}
  </ul>
  <div class="new">
    <input placeholder="New folder" bind:value={newFolder} on:keydown={(e)=>{ if(e.key==='Enter') createFolder(); }} />
    <button on:click={createFolder}>Add</button>
  </div>
</aside>

<style>
  .folders { width: 220px; flex: 0 0 220px; border: 1px solid #e5e7eb; border-radius: 8px; padding: .5rem; background:#fff; }
  .hdr { font-weight: 700; margin-bottom: .25rem; }
  .all, .unfiled { width:100%; text-align:left; background:#f8fafc; border:1px solid #e5e7eb; border-radius:6px; padding:.35rem .5rem; cursor:pointer; display:flex; justify-content:space-between; align-items:center; }
  ul { list-style:none; padding:0; margin:.5rem 0; display:flex; flex-direction:column; gap:.25rem; }
  li button { width:100%; text-align:left; background:#fff; border:1px solid #e5e7eb; border-radius:6px; padding:.35rem .5rem; cursor:pointer; display:flex; justify-content:space-between; align-items:center; }
  button.active { background:#eef2ff; border-color:#c7d2fe; color:#4338ca; font-weight:600; }
  .new { display:flex; gap:.35rem; }
  .new input { flex:1; padding:.3rem .5rem; border:1px solid #e5e7eb; border-radius:6px; }
  .new button { padding:.3rem .5rem; border:1px solid #e5e7eb; background:#f3f4f6; border-radius:6px; cursor:pointer; }
</style>
