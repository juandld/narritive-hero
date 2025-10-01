<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let includeDate: boolean;
  export let includePlace: boolean;
  export let isRecording: boolean;
  export let layout: 'list' | 'compact' | 'grid3' = 'list';

  const dispatch = createEventDispatcher();

  function triggerUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const files = input.files ? Array.from(input.files) : [];
    dispatch('uploadFiles', files);
    // reset input so the same file can be selected again
    if (input) input.value = '';
  }
</script>

<div class="topbar">
  <div class="row">
    <div class="actions" style="margin-left:auto">
      <input id="toolbar-upload" type="file" accept="audio/*" multiple style="display:none" on:change={triggerUpload} />
      <button class="btn" on:click={() => (document.getElementById('toolbar-upload') as HTMLInputElement)?.click()}>Upload</button>
      <button class="btn" on:click={() => dispatch('openNarratives')}>Narratives</button>
      <button class="btn" on:click={() => dispatch('openFormats')}>Formats</button>
    </div>
  </div>
  <div class="row record">
    <label class="chk"><input type="checkbox" bind:checked={includeDate} /> Include date</label>
    <label class="chk"><input type="checkbox" bind:checked={includePlace} /> Include place</label>
    {#if isRecording}
      <button class="btn danger" on:click={() => dispatch('stopRecording')}>Stop Recording</button>
    {:else}
      <button class="btn primary" on:click={() => dispatch('startRecording')}>Start Recording</button>
    {/if}
    <div class="spacer"></div>
    <div class="view">
      <span>View:</span>
      <div class="seg">
        <button class:active={layout==='list'} on:click={() => (layout='list')}>List</button>
        <button class:active={layout==='compact'} on:click={() => (layout='compact')}>Compact</button>
        <button class:active={layout==='grid3'} on:click={() => (layout='grid3')}>Grid x3</button>
      </div>
    </div>
  </div>
</div>

<style>
  .topbar { border:1px solid #e5e7eb; border-radius:12px; padding:.75rem 1rem; background:#fff; margin-bottom: 1rem; }
  .row { display:flex; align-items:center; gap:.75rem; justify-content: space-between; flex-wrap: wrap; }
  .row.record { gap: 1rem; }
  .actions { display:flex; gap:.5rem; }
  .btn { border:1px solid #e5e7eb; background:#f9fafb; border-radius:8px; padding:.4rem .8rem; cursor:pointer; }
  .btn.primary { background:#3B82F6; color:#fff; border-color:#3B82F6; }
  .btn.danger { background:#db4437; color:#fff; border-color:#db4437; }
  .chk { display:flex; align-items:center; gap:.35rem; color:#374151; }
  .spacer { flex:1 1 auto; }
  .view { display:flex; align-items:center; gap:.5rem; }
  .view .seg { display:inline-flex; border:1px solid #e5e7eb; border-radius:8px; overflow:hidden; }
  .view .seg button { border:none; padding:.35rem .6rem; background:#fff; cursor:pointer; }
  .view .seg button.active { background:#eef2ff; color:#4338ca; font-weight:600; }
</style>

