<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Modal from '$lib/components/common/Modal.svelte';
  export let open = false;
  export let name = '';
  export let count = 0;
  const dispatch = createEventDispatcher();
  let input = '';
  function close(){ dispatch('close'); input=''; }
  function confirm(){ if(input.trim().toLowerCase()==='delete') dispatch('confirm'); }
</script>

<Modal {open} title={`Delete folder “${name}”?`} on:close={close} width="min(520px, 92vw)">
  <div class="content">
    <p>This will permanently delete {count} note{count===1?'':'s'} inside this folder (audio and transcriptions). This cannot be undone.</p>
    <label class="confirm">Type <code>delete</code> to confirm</label>
    <input class="field" bind:value={input} placeholder="delete" />
    <div class="actions">
      <button class="ghost" on:click={close}>Cancel</button>
      <button class="danger" disabled={input.trim().toLowerCase()!=='delete'} on:click={confirm}>Delete</button>
    </div>
  </div>
</Modal>

<style>
  .content { word-break: break-word; overflow-wrap: anywhere; }
  .confirm { display:block; margin:.5rem 0 .25rem 0; color:#6b7280; }
  .field { width:100%; max-width:100%; box-sizing:border-box; display:block; border:1px solid #e5e7eb; border-radius:8px; padding:.45rem .6rem; }
  .actions { display:flex; justify-content:flex-end; gap:.5rem; margin-top:.75rem; }
  .ghost { background:#f3f4f6; color:#111; border:1px solid #e5e7eb; padding:.45rem .75rem; border-radius:8px; cursor:pointer; }
  .danger { background:#ef4444; color:#fff; border:none; padding:.45rem .75rem; border-radius:8px; cursor:pointer; }
</style>
