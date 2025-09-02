<script lang="ts">
  import NoteItem from './NoteItem.svelte';
  import { createEventDispatcher } from 'svelte';

  export let notes: any[];
  export let expandedNotes: Set<string>;
  export let selectedNotes: Set<string>;

  const dispatch = createEventDispatcher();

  function toggleExpand(filename: string) {
    dispatch('toggle', filename);
  }

  function copyToClipboard(transcription: string | undefined) {
    dispatch('copy', transcription);
  }

  function deleteNote(filename: string) {
    dispatch('delete', filename);
  }

  function selectNote(event: CustomEvent<{ filename: string; selected: boolean }>) {
    dispatch('select', event.detail);
  }
</script>

<h2>Saved Notes</h2>
{#if notes.length > 0}
  <ul style="list-style: none; padding: 0;">
    {#each notes as note}
      <NoteItem
        {note}
        expanded={expandedNotes.has(note.filename)}
        selected={selectedNotes.has(note.filename)}
        on:toggle={() => toggleExpand(note.filename)}
        on:copy={() => copyToClipboard(note.transcription)}
        on:delete={() => deleteNote(note.filename)}
        on:select={selectNote}
      />
    {/each}
  </ul>
{:else}
  <p>No notes found. Record one above!</p>
{/if}
