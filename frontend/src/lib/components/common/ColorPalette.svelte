<script lang="ts">
  export let colors: { label: string; value: string }[] = [];
  export let selected: string = '';
  export let size: 'small' | 'default' = 'small';
  export let ariaLabel = 'Color palette';
  export let onPick: (value: string) => void;
  function pick(v: string){ onPick && onPick(v); }
</script>

<div class="palette" class:small={size==='small'} role="listbox" aria-label={ariaLabel}>
  {#each colors as c}
    <button
      type="button"
      class:selected={selected===c.value}
      on:click={() => pick(c.value)}
      style={`background:${c.value}`}
      aria-label={c.label}
      role="option"
      aria-selected={selected===c.value}
    ></button>
  {/each}
  <slot />
</div>

<style>
  .palette { display:inline-flex; gap:6px; padding:6px; border:1px solid #e5e7eb; border-radius:9999px; background:#fff; }
  .palette.small { gap:6px; }
  .palette button { width:34px; height:18px; border-radius:9999px; border:2px solid #fff; cursor:pointer; }
  .palette button.selected { border-color:#111; box-shadow: 0 0 0 1px #111 inset; }
  .palette button:focus-visible { outline:2px solid #111; outline-offset:2px; }
</style>

