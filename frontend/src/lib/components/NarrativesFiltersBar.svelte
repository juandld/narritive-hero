<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  type NF = { search: string; folder: string };
  let { filters = $bindable<NF>({ search: '', folder: '__ALL__' }), folders = [] as string[], counts = { total: 0, filtered: 0 } } = $props();

  const dispatch = createEventDispatcher();
  function emit() { dispatch('change', { ...filters }); }
  function selectAll() { dispatch('selectAll'); }
  function clearSelection() { dispatch('clearSelection'); }
  function reset() { filters = { search: '', folder: '__ALL__' }; emit(); }
</script>

<div class="filters">
  <div class="field search">
    <label for="nf-search">Search</label>
    <input id="nf-search" placeholder="search title or file" value={filters.search} oninput={(e)=>{ filters = { ...filters, search: (e.target as HTMLInputElement).value }; emit(); }} />
  </div>
  <div class="field">
    <label for="nf-folder">Folder</label>
    <select id="nf-folder" bind:value={filters.folder} onchange={emit}>
      <option value="__ALL__">All</option>
      <option value="__UNFILED__">Unfiled</option>
      {#each folders as f}
        <option value={f}>{f}</option>
      {/each}
    </select>
  </div>
  <div class="actions">
    <button type="button" class="reset-button" onclick={reset}>Reset</button>
    <div class="select-actions">
      <button type="button" class="sel" title="Select all filtered" onclick={selectAll}>Select all ({counts.filtered})</button>
      <button type="button" class="sel" title="Clear selection" onclick={clearSelection}>Clear</button>
    </div>
    <div class="results-info">{counts.filtered} of {counts.total}</div>
  </div>
</div>

<style>
  .filters {
    display: grid;
    grid-template-columns: repeat(6, minmax(140px, 1fr));
    grid-auto-rows: min-content;
    gap: 0.75rem 0.75rem;
    margin-bottom: 1rem;
    align-items: end;
    background: #f8f9fa;
    border: 1px solid #e5e7eb;
    padding: 0.75rem;
    border-radius: 8px;
    box-sizing: border-box;
  }
  .filters * { min-width: 0; }
  .field { min-width: 0; display: flex; flex-direction: column; }
  .field label { display: block; font-size: 0.8rem; color: #555; }
  .field input, .field select { width: 100%; min-width: 0; box-sizing: border-box; }
  .field.search { grid-column: span 3; }
  .actions { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 0.75rem; grid-column: 1 / -1; }
  .reset-button { background: #6c757d; color: white; border: none; padding: 0.5rem 0.9rem; border-radius: 6px; cursor: pointer; }
  .select-actions { grid-column: 1; display:flex; flex-wrap: wrap; gap:.35rem; min-width: 0; }
  .sel { background:#fff; color:#374151; border:1px solid #e5e7eb; padding: .35rem .6rem; border-radius: 6px; cursor: pointer; }
  .results-info { grid-column: 1; font-size: 0.85rem; color: #666; white-space: nowrap; }
  @media (max-width: 900px) {
    .filters { grid-template-columns: repeat(3, minmax(140px, 1fr)); }
    .field.search { grid-column: span 3; }
  }
  @media (max-width: 600px) {
    .filters { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
    .field.search { grid-column: span 2; }
    .actions { grid-template-columns: 1fr; }
    .results-info { grid-column: 1; justify-self: end; }
  }
</style>
