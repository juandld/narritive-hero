<script lang="ts">
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';

  export let src: string;

  const dispatch = createEventDispatcher();
  let audioEl: HTMLAudioElement | null = null;
  let duration = 0;
  let current = 0;
  let dragging = false;
  let wasPlayingBeforeDrag = false;
  let isLoaded = false;
  let isPlaying = false;

  function fmt(t: number) {
    if (!isFinite(t) || t < 0) return '0:00';
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  function onPlay() {
    isPlaying = true;
    // Pause all other audio elements when this starts playing
    try {
      const els = document.querySelectorAll('audio.note-audio');
      els.forEach((el) => {
        if (audioEl && el !== audioEl && !(el as HTMLAudioElement).paused) {
          (el as HTMLAudioElement).pause();
        }
      });
    } catch {}
    dispatch('play');
  }
  function onPause() { isPlaying = false; dispatch('pause'); }
  function onEnded() { isPlaying = false; dispatch('ended'); }
  function onLoaded() {
    isLoaded = true;
    duration = audioEl?.duration || 0;
    dispatch('loaded');
  }
  function onEmptied() { isLoaded = false; isPlaying = false; duration = 0; current = 0; dispatch('emptied'); }
  function onTime() { if (!dragging) current = audioEl?.currentTime || 0; }

  function toggle() {
    if (!audioEl) return;
    if (audioEl.paused) audioEl.play(); else audioEl.pause();
  }

  function seekToFraction(frac: number) {
    if (!audioEl || !isFinite(duration) || duration <= 0) return;
    const t = Math.max(0, Math.min(1, frac)) * duration;
    audioEl.currentTime = t;
    current = t;
  }

  function onBarClick(e: MouseEvent) {
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    const frac = (e.clientX - rect.left) / rect.width;
    seekToFraction(frac);
  }

  function onBarPointerDown(e: PointerEvent) {
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    dragging = true;
    wasPlayingBeforeDrag = !!audioEl && !audioEl.paused;
    if (wasPlayingBeforeDrag) audioEl?.pause();
    const move = (ev: PointerEvent) => {
      const frac = (ev.clientX - rect.left) / rect.width;
      seekToFraction(frac);
    };
    const up = (ev: PointerEvent) => {
      const frac = (ev.clientX - rect.left) / rect.width;
      seekToFraction(frac);
      dragging = false;
      if (wasPlayingBeforeDrag) audioEl?.play();
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }

  onMount(() => {
    const a = audioEl;
    if (!a) return;
    a.addEventListener('play', onPlay);
    a.addEventListener('pause', onPause);
    a.addEventListener('ended', onEnded);
    a.addEventListener('loadedmetadata', onLoaded);
    a.addEventListener('emptied', onEmptied);
    a.addEventListener('timeupdate', onTime);
  });
  onDestroy(() => {
    const a = audioEl;
    if (!a) return;
    a.removeEventListener('play', onPlay);
    a.removeEventListener('pause', onPause);
    a.removeEventListener('ended', onEnded);
    a.removeEventListener('loadedmetadata', onLoaded);
    a.removeEventListener('emptied', onEmptied);
    a.removeEventListener('timeupdate', onTime);
  });
</script>

<div class="ap" on:click|stopPropagation on:mousedown|stopPropagation>
  <audio class="note-audio" bind:this={audioEl} src={src} preload="metadata"></audio>
  <button class="ap-btn" aria-label={isPlaying ? 'Pause' : 'Play'} on:click={toggle}>
    {#if isPlaying}
      
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><rect x="6" y="4" width="4" height="16" rx="1" fill="#111"/><rect x="14" y="4" width="4" height="16" rx="1" fill="#111"/></svg>
    {:else}
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M8 5v14l11-7-11-7z" fill="#111"/></svg>
    {/if}
  </button>
  <div class="ap-bar" role="slider" aria-valuemin="0" aria-valuemax={duration} aria-valuenow={current} on:click={onBarClick} on:pointerdown={onBarPointerDown}
    style="--pct:{duration>0? (current/duration*100) : 0}%;">
    <div class="ap-track {isPlaying ? 'playing' : (isLoaded ? 'loaded' : '')}"></div>
    <div class="ap-progress {isPlaying ? 'playing' : (isLoaded ? 'loaded' : '')}" style="width: var(--pct);"></div>
  </div>
  <div class="ap-time">{fmt(current)} / {fmt(duration)}</div>
</div>

<style>
  .ap { display:flex; align-items:center; gap:.5rem; background:#fff; border:2px solid #e5e7eb; border-radius:6px; padding:.4rem .6rem; margin-bottom:.5rem; }
  .ap-btn { background:#e8f0fe; border:1px solid #dbe7ff; border-radius:6px; width:32px; height:32px; display:grid; place-items:center; cursor:pointer; }
  .ap-btn:hover { filter: brightness(0.98); }
  .ap-bar { position:relative; height:8px; flex:1; border-radius:999px; background:transparent; cursor:pointer; }
  .ap-track { position:absolute; inset:0; border-radius:999px; background:#e5e7eb; }
  .ap-track.loaded { background:#e8f0fe; }
  .ap-track.playing { background:#d1fae5; }
  .ap-progress { position:absolute; left:0; top:0; bottom:0; width:0; border-radius:999px; background:#93C5FD; }
  .ap-progress.loaded { background:#93C5FD; /* sky-300 */ }
  .ap-progress.playing { background:#10B981; /* emerald-500 */ }
  .ap-time { font-variant-numeric: tabular-nums; color:#555; font-size:.85rem; min-width: 72px; text-align:right; }
</style>
