<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let note: {
    filename: string;
    transcription?: string;
    title?: string;
  };
  export let expanded: boolean;
  export let selected: boolean;

  const dispatch = createEventDispatcher();

  const BACKEND_URL = 'http://localhost:8000';

  function toggleExpand() {
    dispatch('toggle');
  }

  function copyToClipboard() {
    dispatch('copy');
  }

  function deleteNote() {
    dispatch('delete');
  }

  function onSelect() {
    dispatch('select', { filename: note.filename, selected: !selected });
  }
</script>

<li style="margin-bottom: 1.5rem; padding: 1rem; background-color: #f1f3f4; border-radius: 8px;">
  <input type="checkbox" checked={selected} on:change={onSelect} />
  {#if note.title}
    <p><strong>Title:</strong> {note.title}</p>
  {/if}
  <audio controls src="{`${BACKEND_URL}/voice_notes/${note.filename}`}" style="width: 100%; margin-bottom: 0.5rem;"></audio>
  <blockquote style="background-color: white; padding: 0.5rem 1rem; border-left: 5px solid #4285f4; margin: 0;">
    <p>{expanded ? note.transcription : ''}</p>
    {#if note.transcription && note.transcription.length > 0}
      <button
        on:click={toggleExpand}
        style="background: none; border: none; color: #4285f4; cursor: pointer; font-size: 0.9em; transform: rotate({expanded ? '180deg' : '0deg'});"
      >
        {expanded ? '\u25B2' : '\u25BC'}
      </button>
    {/if}
  </blockquote>
  <button
    on:click={copyToClipboard}
    style="background-color: #4285f4; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px;"
    >Copy TS</button
  >
  <button
    on:click={deleteNote}
    style="background-color: #db4437; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; margin-left: 10px;"
    >Delete</button
  >
</li>
