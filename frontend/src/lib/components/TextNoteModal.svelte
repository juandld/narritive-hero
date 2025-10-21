<script lang="ts">
  import Modal from '$lib/components/common/Modal.svelte';
  import { createEventDispatcher } from 'svelte';
  export let open = false;
  const dispatch = createEventDispatcher();

  let title = '';
  let transcription = '';
  let folder = '';
  let folders: { name: string; count: number }[] = [];
  let creatingFolder = false;
  let newFolder = '';

  import { api } from '$lib/api';
  import { onMount } from 'svelte';
  async function loadFolders(){ try { folders = await api.getFolders(); } catch { folders = []; } }
  onMount(loadFolders);
  $: if (open) { loadFolders(); }

  function close(){ dispatch('close'); }
  async function submit(){
    const t = (transcription || '').trim();
    if (!t) return;
    let chosen = (folder || '').trim();
    if (creatingFolder) {
      const nf = (newFolder || '').trim();
      if (nf) {
        try { await api.createFolder(nf); chosen = nf; } catch {}
      }
    }
    dispatch('create', { title: (title||'').trim(), transcription: t, folder: chosen });
  }
</script>

<Modal {open} title="New Text Note" on:close={close}>
  <div class="form">
    <label>Title
      <input type="text" bind:value={title} placeholder="Optional title" />
    </label>
    <label>Folder
      {#if !creatingFolder}
        <select bind:value={folder}>
          <option value="">(No folder)</option>
          {#each folders as f}
            <option value={f.name}>{f.name}</option>
          {/each}
        </select>
        <button class="btn" on:click={() => { creatingFolder = true; newFolder=''; }}>New folder…</button>
      {:else}
        <div class="inline">
          <input type="text" bind:value={newFolder} placeholder="New folder name" />
          <button class="btn" on:click={() => { creatingFolder = false; }}>Cancel</button>
        </div>
      {/if}
    </label>
    <label>Transcription
      <textarea bind:value={transcription} rows="10" placeholder="Paste or type your text..."></textarea>
    </label>
    <div class="actions">
      <button class="btn" on:click={close}>Cancel</button>
      <button class="btn primary" on:click={submit}>Create</button>
    </div>
  </div>
</Modal>

<style>
  .form { display:flex; flex-direction: column; gap:.75rem; }
  label { display:flex; flex-direction: column; gap:.35rem; font-size:.9rem; }
  input, textarea, select { width:100%; box-sizing:border-box; border:1px solid #e5e7eb; border-radius:8px; padding:.5rem .6rem; font: inherit; }
  .inline { display:flex; gap:.5rem; align-items:center; }
  .actions { display:flex; gap:.5rem; justify-content:flex-end; margin-top:.5rem; }
  .btn { border:1px solid #e5e7eb; background:#f9fafb; border-radius:8px; padding:.4rem .8rem; cursor:pointer; }
  .btn.primary { background:#3B82F6; color:#fff; border-color:#3B82F6; }
</style>
