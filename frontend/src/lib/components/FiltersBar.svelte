<script lang="ts">
  // Compact, reusable filter bar. Emits a 'change' event with the current filters.
  import { createEventDispatcher } from 'svelte';
  import type { Filters } from '$lib/stores/filters';

  let { filters = $bindable<Filters>({
    dateFrom: '',
    dateTo: '',
    topics: '',
    minLen: '' as any,
    maxLen: '' as any,
    search: '',
    sortKey: 'date',
    sortDir: 'desc'
  }), counts = { total: 0, filtered: 0 } } = $props();

  // Operate directly on bindable `filters`

  const dispatch = createEventDispatcher();
  function emit() {
    dispatch('change', { ...filters });
  }
  function selectAll() { dispatch('selectAll'); }
  function clearSelection() { dispatch('clearSelection'); }
  function reset() {
    filters = { dateFrom: '', dateTo: '', topics: '', minLen: '' as any, maxLen: '' as any, search: '', sortKey: 'date', sortDir: 'desc' };
    emit();
  }
  // No reactive sync needed in runes mode
</script>

<div class="filters">
  <div class="field">
    <label for="f-date-from">Date from</label>
    <input id="f-date-from" type="date" value={filters.dateFrom} on:change={(e) => { filters = { ...filters, dateFrom: (e.target as HTMLInputElement).value }; emit(); }} />
  </div>
  <div class="field">
    <label for="f-date-to">Date to</label>
    <input id="f-date-to" type="date" value={filters.dateTo} on:change={(e) => { filters = { ...filters, dateTo: (e.target as HTMLInputElement).value }; emit(); }} />
  </div>
  <div class="field">
    <label for="f-topics">Topics</label>
    <input id="f-topics" placeholder="e.g. meeting, travel" value={filters.topics} on:input={(e) => { filters = { ...filters, topics: (e.target as HTMLInputElement).value }; emit(); }} />
  </div>
  <div class="field">
    <label for="f-min">Min sec</label>
    <input id="f-min" type="number" min="0" value={filters.minLen} on:input={(e) => { const v = (e.target as HTMLInputElement).value; filters = { ...filters, minLen: v === '' ? '' : Number(v) as any }; emit(); }} />
  </div>
  <div class="field">
    <label for="f-max">Max sec</label>
    <input id="f-max" type="number" min="0" value={filters.maxLen} on:input={(e) => { const v = (e.target as HTMLInputElement).value; filters = { ...filters, maxLen: v === '' ? '' : Number(v) as any }; emit(); }} />
  </div>
  <div class="field search">
    <label for="f-search">Search</label>
    <input id="f-search" placeholder="search title or text" value={filters.search} on:input={(e) => { filters = { ...filters, search: (e.target as HTMLInputElement).value }; emit(); }} />
  </div>
  <div class="field">
    <label for="f-sort">Sort by</label>
    <div class="sort-row">
      <select id="f-sort" bind:value={filters.sortKey} on:change={() => { filters = { ...filters }; emit(); }}>
        <option value="date">Date</option>
        <option value="type">Type</option>
        <option value="length">Length</option>
        <option value="language">Language</option>
      </select>
      <select bind:value={filters.sortDir} on:change={() => { filters = { ...filters }; emit(); }}>
        <option value="asc">Asc</option>
        <option value="desc">Desc</option>
      </select>
    </div>
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
    grid-template-columns: repeat(7, minmax(140px, 1fr));
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
  .field input {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .field.search { grid-column: span 2; }
  .sort-row { display:flex; gap:.35rem; }
  .actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.75rem;
    grid-column: 1 / -1; /* full width */
  }
  .actions > * { min-width: 0; }
  .reset-button { grid-column: 1; }
  .select-actions { grid-column: 1; display:flex; flex-wrap: wrap; gap:.35rem; min-width: 0; }
  .sel { white-space: nowrap; max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
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
    grid-column: 1;
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
    .actions { grid-template-columns: 1fr; }
    .results-info { grid-column: 1; justify-self: end; }
  }
</style>
