<script lang="ts">
  import NoteItem from './NoteItem.svelte';
  import FolderCard from './FolderCard.svelte';
  import NewFolderCard from './NewFolderCard.svelte';
  import { createEventDispatcher } from 'svelte';
  import Breadcrumbs from '$lib/components/common/Breadcrumbs.svelte';

  export let notes: any[];
  export let expandedNotes: Set<string>;
  export let selectedNotes: Set<string>;
  export let layout: 'list' | 'compact' | 'grid3' = 'list';
  export let folders: { name: string; count: number }[] = [];
  export let showFolders: boolean = true;
  export let selectedFolder: string = '__UNFILED__';

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

  function selectNote(event: CustomEvent<{ filename: string; selected: boolean; index: number; shift?: boolean }>) {
    dispatch('select', event.detail);
  }
</script>

{#if selectedFolder !== '__ALL__' && selectedFolder !== '__UNFILED__'}
  <Breadcrumbs
    segments={[{label:'All'},{label:selectedFolder, current:true}]}
    on:navigate={(e)=>{ if(e.detail.index===0) dispatch('navAll'); }}
  />
{/if}

{#if showFolders}
  <h2>Folders</h2>
  <ul class:as-grid={layout === 'grid3'} class:compact={layout !== 'list'}>
    <NewFolderCard on:create={(e)=>dispatch('createFolder', e.detail)} on:createAndMove={(e)=>dispatch('createFolderAndMove', e.detail)} />
    {#each folders as f}
      <FolderCard name={f.name} count={f.count} layout={layout === 'list' ? 'full' : 'compact'} on:moveToFolder={(e)=>dispatch('moveToFolder', e.detail)} on:delete={(e)=>dispatch('deleteFolder', e.detail)} on:open={(e)=>dispatch('openFolder', e.detail)} />
    {/each}
  </ul>
{/if}

<h2>Saved Notes</h2>
{#if notes.length > 0}
  <ul class:as-grid={layout === 'grid3'} class:compact={layout !== 'list'}>
    {#each notes as note, i}
      <NoteItem
        {note}
        expanded={expandedNotes.has(note.filename)}
        selected={selectedNotes.has(note.filename)}
        index={i}
        variant={layout === 'list' ? 'full' : 'compact'}
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

<style>
  ul { list-style: none; padding: 0; margin: 0; }
  h2 { margin: .75rem 0 .5rem 0; font-size: 1.1rem; }
  /* breadcrumbs now a component */
  ul.as-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
  }
  @media (max-width: 900px) { ul.as-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 600px) { ul.as-grid { grid-template-columns: repeat(1, minmax(0, 1fr)); } }
  ul.compact :global(li) { margin-bottom: 0.75rem !important; }
</style>
