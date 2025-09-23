<script lang="ts">
  // Compact, reusable filter bar. Emits a 'change' event with the current filters.
  import { createEventDispatcher } from 'svelte';

  export type Filters = {
    dateFrom: string;
    dateTo: string;
    topics: string;
    minLen: number | '';
    maxLen: number | '';
    search: string;
  };

  export let filters: Filters = {
    dateFrom: '',
    dateTo: '',
    topics: '',
    minLen: '',
    maxLen: '',
    search: ''
  };

  export let counts: { total: number; filtered: number } = { total: 0, filtered: 0 };

  const dispatch = createEventDispatcher();
  function emit() { dispatch('change', { ...filters }); }
  function reset() {
    filters = { dateFrom: '', dateTo: '', topics: '', minLen: '', maxLen: '', search: '' };
    emit();
  }
</script>

<div class="filters">
  <div class="field">
    <label for="f-date-from">Date from</label>
    <input id="f-date-from" type="date" bind:value={filters.dateFrom} on:change={emit} />
  </div>
  <div class="field">
    <label for="f-date-to">Date to</label>
    <input id="f-date-to" type="date" bind:value={filters.dateTo} on:change={emit} />
  </div>
  <div class="field">
    <label for="f-topics">Topics</label>
    <input id="f-topics" placeholder="e.g. meeting, travel" bind:value={filters.topics} on:input={emit} />
  </div>
  <div class="field">
    <label for="f-min">Min sec</label>
    <input id="f-min" type="number" min="0" bind:value={filters.minLen} on:input={emit} />
  </div>
  <div class="field">
    <label for="f-max">Max sec</label>
    <input id="f-max" type="number" min="0" bind:value={filters.maxLen} on:input={emit} />
  </div>
  <div class="field search">
    <label for="f-search">Search</label>
    <input id="f-search" placeholder="search title or text" bind:value={filters.search} on:input={emit} />
  </div>
  <div class="actions">
    <button type="button" class="reset-button" on:click={reset}>Reset Filters</button>
    <div class="results-info">{counts.filtered} of {counts.total}</div>
  </div>
</div>

<style>
  .filters {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.75rem 0.75rem;
    margin-bottom: 1rem;
    align-items: end;
    background: #f8f9fa;
    border: 1px solid #e5e7eb;
    padding: 0.75rem;
    border-radius: 8px;
  }
  .field label {
    display: block;
    font-size: 0.8rem;
    color: #555;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.75rem;
  }
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
  }
</style>

