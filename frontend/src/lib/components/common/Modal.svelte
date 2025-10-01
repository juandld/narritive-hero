<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  export let open = false;
  export let title: string | null = null;
  export let width = 'min(800px, 92vw)';
  export let closeOnBackdrop = true;
  export let closeOnEsc = true;
  const dispatch = createEventDispatcher();
  let modalEl: HTMLDivElement | null = null;

  function close(){ dispatch('close'); }
  function onKey(e: KeyboardEvent){ if (closeOnEsc && e.key === 'Escape') close(); }
  function onOverlayClick(){ if (closeOnBackdrop) close(); }
</script>

{#if open}
  <div class="modal-overlay" on:click={onOverlayClick}></div>
  <div class="modal" style={`width:${width}`} role="dialog" aria-modal="true" on:keydown={onKey} tabindex="-1" bind:this={modalEl}>
    {#if title}
      <div class="modal-header">
        <h3>{title}</h3>
        <button class="x" on:click={close} aria-label="Close">×</button>
      </div>
    {/if}
    <div class="modal-content">
      <slot />
    </div>
    <slot name="footer" />
  </div>
{/if}

<style>
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 1000; }
  .modal { position: fixed; top: 8vh; left: 50%; transform: translateX(-50%);
           background: #fff; padding: 1rem; border-radius: 10px; z-index: 1001; box-shadow: 0 10px 30px rgba(0,0,0,.2);
           max-height: 84vh; display: flex; flex-direction: column; overflow: hidden; }
  .modal-header { display:flex; align-items:center; justify-content: space-between; margin-bottom:.5rem; }
  h3 { margin: 0; }
  .x { background:none; border:none; font-size:1.2rem; cursor:pointer; }
  .modal-content { overflow:auto; min-height:0; }
</style>

