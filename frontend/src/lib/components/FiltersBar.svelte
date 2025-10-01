<script lang="ts">
  // Compact, reusable filter bar. Emits a 'change' event with the current filters.
  import { createEventDispatcher } from 'svelte';
  import type { Filters } from '$lib/stores/filters';

  export let filters: Filters = {
    dateFrom: '',
    dateTo: '',
    topics: '',
    minLen: '',
    maxLen: '',
    search: ''
  };

  // Local, mutable copy for Svelte 5 (avoid binding directly to props)
  let local = { ...filters } as Filters;

  export let counts: { total: number; filtered: number } = { total: 0, filtered: 0 };

  const dispatch = createEventDispatcher();
  function emit() {
    dispatch('change', { ...local });
  }
  function selectAll() { dispatch('selectAll'); }
  function clearSelection() { dispatch('clearSelection'); }
  function reset() {
    local = { dateFrom: '', dateTo: '', topics: '', minLen: '', maxLen: '', search: '' };
    emit();
  }

  // Keep local state in sync if parent replaces filters
  $: if (filters !== local) {
    // shallow compare by reference; assign when parent updates
    local = { ...filters };
  }
</script>

<div class="filters">
  <div class="field">
    <label for="f-date-from">Date from</label>
    <input id="f-date-from" type="date" value={local.dateFrom} on:change={(e) => { local.dateFrom = (e.target as HTMLInputElement).value; emit(); }} />
  </div>
  <div class="field">
    <label for="f-date-to">Date to</label>
    <input id="f-date-to" type="date" value={local.dateTo} on:change={(e) => { local.dateTo = (e.target as HTMLInputElement).value; emit(); }} />
  </div>
  <div class="field">
    <label for="f-topics">Topics</label>
    <input id="f-topics" placeholder="e.g. meeting, travel" value={local.topics} on:input={(e) => { local.topics = (e.target as HTMLInputElement).value; emit(); }} />
  </div>
  <div class="field">
    <label for="f-min">Min sec</label>
    <input id="f-min" type="number" min="0" value={local.minLen} on:input={(e) => { const v = (e.target as HTMLInputElement).value; local.minLen = v === '' ? '' : Number(v); emit(); }} />
  </div>
  <div class="field">
    <label for="f-max">Max sec</label>
    <input id="f-max" type="number" min="0" value={local.maxLen} on:input={(e) => { const v = (e.target as HTMLInputElement).value; local.maxLen = v === '' ? '' : Number(v); emit(); }} />
  </div>
  <div class="field search">
    <label for="f-search">Search</label>
    <input id="f-search" placeholder="search title or text" value={local.search} on:input={(e) => { local.search = (e.target as HTMLInputElement).value; emit(); }} />
  </div>
  <div class="actions">
    <button type="button" class="reset-button" on:click={reset}>Reset Filters</button>
    <div class="select-actions">
      <button type="button" class="sel" title="Select all filtered" on:click={selectAll}>Select all ({counts.filtered})</button>
      <button type="button" class="sel" title="Clear selection" on:click={clearSelection}>Clear</button>
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
  .field label {
    display: block;
    font-size: 0.8rem;
    color: #555;
  }
  .field input,
  .field select {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .field.search { grid-column: span 2; }
  .actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    grid-column: 1 / -1; /* full width */
    flex-wrap: wrap;
  }
  .select-actions { display:flex; gap:.35rem; }
  .sel { background:#fff; color:#374151; border:1px solid #e5e7eb; padding: .35rem .6rem; border-radius: 6px; cursor: pointer; }
  .reset-button {
    background: #6c757d;
    color: white;
    border: none;
    padding: 0.5rem 0.9rem;
    border-radius: 6px;
    cursor: pointer;
  }
  .results-info {
    font-size: 0.85rem;
    color: #666;
    white-space: nowrap;
  }
  @media (max-width: 900px) {
    .filters { grid-template-columns: repeat(3, minmax(140px, 1fr)); }
    .field.search { grid-column: span 3; }
  }
  @media (max-width: 600px) {
    .filters { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
    .field.search { grid-column: span 2; }
  }
</style>
