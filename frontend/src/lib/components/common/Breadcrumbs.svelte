<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  export let segments: { label: string; current?: boolean }[] = [];
  const dispatch = createEventDispatcher();
</script>

<nav class="breadcrumbs" aria-label="Breadcrumb">
  {#each segments as seg, i}
    {#if i > 0}<span class="sep">&gt;</span>{/if}
    {#if seg.current}
      <span class="crumb current">{seg.label}</span>
    {:else}
      <button class="crumb" on:click={() => dispatch('navigate', { index: i, label: seg.label })}>{seg.label}</button>
    {/if}
  {/each}
</nav>

<style>
  .breadcrumbs { display:flex; align-items:center; gap:.35rem; margin:.25rem 0; color:#374151; }
  .crumb { background:none; border:none; color:#374151; cursor:pointer; padding:0; font-size:.95rem; }
  .crumb.current { font-weight:600; color:#4338ca; }
  .sep { color:#9ca3af; }
</style>

