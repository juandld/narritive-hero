<script lang="ts">
  export let colors: { label: string; value: string }[] = [];
  export let selected: string = '';
  export let size: 'small' | 'default' = 'small';
  export let ariaLabel = 'Color palette';
  export let onPick: (value: string) => void;
  function pick(v: string){ onPick && onPick(v); }
  let container: HTMLDivElement | null = null;

  function focusOptions(){
    if (!container) return [] as HTMLButtonElement[];
    return Array.from(container.querySelectorAll('button[role="option"]')) as HTMLButtonElement[];
  }
  function onKeydown(e: KeyboardEvent){
    const opts = focusOptions();
    if (!opts.length) return;
    const active = (document.activeElement as HTMLElement) || null;
    const idx = active ? opts.indexOf(active as HTMLButtonElement) : -1;
    let next = idx;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { next = idx < 0 ? 0 : Math.min(opts.length - 1, idx + 1); e.preventDefault(); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { next = idx < 0 ? 0 : Math.max(0, idx - 1); e.preventDefault(); }
    else if (e.key === 'Home') { next = 0; e.preventDefault(); }
    else if (e.key === 'End') { next = opts.length - 1; e.preventDefault(); }
    else if (e.key === 'Enter') { if (idx >= 0) { e.preventDefault(); opts[idx].click(); } }
    if (next !== idx && next >= 0) { opts[next].focus(); }
  }
</script>

<div class="palette" class:small={size==='small'} role="listbox" aria-label={ariaLabel} bind:this={container} on:keydown={onKeydown}>
  {#each colors as c}
    <button
      type="button"
      class:selected={selected===c.value}
      on:click={() => pick(c.value)}
      style={`background:${c.value}`}
      aria-label={c.label}
      role="option"
      aria-selected={selected===c.value}
      tabindex={selected===c.value ? 0 : -1}
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
