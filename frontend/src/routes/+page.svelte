<script lang="ts">
  import { onMount } from 'svelte';
  import Toast from '../lib/components/Toast.svelte';
  import PlacePrompt from '../lib/components/PlacePrompt.svelte';
  import NotesList from '../lib/components/NotesList.svelte';
  import NarrativeGenerateModal from '../lib/components/NarrativeGenerateModal.svelte';
  import FormatsManager from '../lib/components/FormatsManager.svelte';
  import TextNoteModal from '../lib/components/TextNoteModal.svelte';
  import Topbar from '$lib/components/topbar/Topbar.svelte';
  import { appActions } from '$lib/services/appActions';
  // Types and filtering handled via stores/derived
  import DeleteFolderModal from '../lib/components/DeleteFolderModal.svelte';
  import { onToggleExpand } from '$lib/handlers/noteHandlers';
  import { notes as notesStore, selectedNotes as selectedNotesStore, notesActions } from '$lib/stores/notes';
  import { folders as foldersStore, selectedFolder as selectedFolderStore } from '$lib/stores/folders';

  import { isRecording as isRecordingStore, includeDate as includeDateStore, includePlace as includePlaceStore, uiAppActions, detectedPlace as detectedPlaceStore, showPlacePrompt as showPlacePromptStore } from '$lib/stores/uiApp';
  // Using stores/derived for notes, folders, filteredNotes, selection, folder
  // Expanded notes state comes from a centralized UI store
  import { expandedNotes as expandedNotesStore } from '$lib/stores/ui';
  let toastMessage = $state('');
  let showToast = $state(false);
  let isUploading = $state(false);
  let isDeleting = $state(false);
  // Multi-file upload progress
  let multiUploadActive = $state(false);
  let multiUploadTotal = $state(0);
  let multiUploadIndex = $state(0);
  const multiUploadPercent = $derived(multiUploadTotal ? Math.floor((multiUploadIndex / multiUploadTotal) * 100) : 0);

  // Drawer removed; navigate to narratives page instead
  let isNarrativeModalOpen = $state(false);
  let isGeneratingNarrative = $state(false);
  let isFormatsOpen = $state(false);
  let isTextNoteOpen = $state(false);
  // Delete folder confirmation
  let dfOpen = $state(false); let dfName = $state(''); let dfCount = $state(0);

  // includeDate/includePlace come from uiApp store; no local binds
  // detectedPlace/showPlacePrompt read from uiApp store in template
  import { pageDrop } from '$lib/actions/pageDrop';
  import { handleFiles as uploadsHandleFiles, uploadBlob as uploadsUploadBlob } from '$lib/services/uploads';

  // Config not needed here; services handle endpoints

  // Filters moved to FiltersBar component
  import FiltersBar from '../lib/components/FiltersBar.svelte';
  import type { Filters } from '$lib/stores/filters';
  import BulkActions from '../lib/components/BulkActions.svelte';
  import { goto } from '$app/navigation';
  import { filters as filtersStore } from '$lib/stores/filters';
  import { computedDurations as durationsStore } from '$lib/stores/durations';
  import { applyFilters } from '$lib/filters';
  let filters: Filters = $state({ dateFrom: '', dateTo: '', topics: '', minLen: '', maxLen: '', search: '', sortKey: 'date', sortDir: 'desc' });
  // Keep global filters store in sync (optional)
  $effect(() => { try { filtersStore.set(filters); } catch {} });
  const filteredNotes = $derived(applyFilters($notesStore as any, filters as any, $selectedFolderStore as string, $durationsStore as any));
  let layout = $state<'list' | 'compact' | 'grid3'>('list');
  // Client-side duration cache (store holds the map)
  // durations are computed and stored via pageActions.refreshAll()
  // Expose selection for DnD ghost
  $effect(() => { if (typeof window !== 'undefined') { (window as any).__selectedNotes = new Set($selectedNotesStore as any); } });


  import { folderActions } from '$lib/stores/folders';

  let lastSelectedIndex: number | null = null;

  import { onSelect as onSelectHandler } from '$lib/handlers/selection';
  import { onPlacePromptResponse } from '$lib/handlers/ui';
  const createNarrative = () => { isNarrativeModalOpen = true; };

  import { generateNarrative as generateNarrativeService } from '$lib/services/narratives';
  import type { GenerateOptions } from '$lib/services/narratives';
  import { onCopy } from '$lib/handlers/clipboard';
  import { onMoveToFolder, onCreateFolder, onCreateFolderAndMove } from '$lib/handlers/folders';


  import { refreshAll, moveToFolder as moveToFolderAction } from '$lib/services/pageActions';
  import { api } from '$lib/api';
  onMount(() => { refreshAll(); });

  import { deleteOne as deleteOneAction, deleteMany as deleteManyAction } from '$lib/services/pageActions';

  async function submitNarrativeGeneration(e: CustomEvent<GenerateOptions>) {
    try {
      isGeneratingNarrative = true;
      const items = Array.from($selectedNotesStore).map((f) => ({ filename: f }));
      const { filename } = await generateNarrativeService(items, e?.detail || {});
      isGeneratingNarrative = false;
      isNarrativeModalOpen = false;
      if (filename) {
        // Navigate to narratives route and open the new narrative
        try { await goto(`/narratives?open=${encodeURIComponent(filename)}`); } catch {}
        toastMessage = 'Narrative created';
        showToast = true; setTimeout(() => (showToast = false), 2500);
      }
    } catch (err) {
      console.error('generate narrative failed', err);
      isGeneratingNarrative = false;
      toastMessage = 'Failed to generate narrative';
      showToast = true;
      setTimeout(() => (showToast = false), 3000);
    }
  }

</script>

<main class="page" use:pageDrop={{ onFiles: uploadsHandleFiles }}>
  <Toast message={toastMessage} show={showToast} />

  <Topbar
    includeDate={$includeDateStore}
    includePlace={$includePlaceStore}
    isRecording={$isRecordingStore}
    bind:layout
    on:startRecording={() => uiAppActions.startRecording()}
    on:stopRecording={() => uiAppActions.stopRecording()}
    on:openNarratives={async () => { try { await goto('/narratives'); } catch { /* fallback drawer removed */ } }}
    on:openFormats={() => (isFormatsOpen = true)}
    on:openTextNote={() => (isTextNoteOpen = true)}
    on:uploadFiles={(e) => uploadsHandleFiles((e.detail as File[]) || [])}
  />

  {#if $showPlacePromptStore}
    {#if $detectedPlaceStore}
      <PlacePrompt detectedPlace={$detectedPlaceStore} on:response={onPlacePromptResponse} />
    {:else}
      <PlacePrompt detectedPlace={''} on:response={onPlacePromptResponse} />
    {/if}
  {/if}

  {#if multiUploadActive}
    <div class="bulk-upload-indicator">
      Uploading {multiUploadIndex} / {multiUploadTotal}…
      <div class="progress"><div class="bar" style="width: {multiUploadPercent}%"></div></div>
    </div>
  {:else if isUploading}
    <div class="loading-indicator">Processing your note, please wait...</div>
  {/if}

  <FiltersBar
    bind:filters
    on:selectAll={() => { selectedNotesStore.set(new Set((filteredNotes || []).map((n) => n.filename))); }}
    on:clearSelection={() => { notesActions.clearSelection(); lastSelectedIndex = null; }}
    counts={{ total: ($notesStore || []).length, filtered: (filteredNotes || []).length }}
  />
  <div style="margin: .25rem 0 .5rem 0; color:#666; font-size:.9rem;">
    Sorting: <strong>{filters.sortKey}</strong> <em>{filters.sortDir}</em> — showing {(filteredNotes || []).length} notes
  </div>
  <!-- legacy filters markup removed -->

  

  <NotesList
    notes={filteredNotes}
    expandedNotes={$expandedNotesStore}
    selectedNotes={$selectedNotesStore}
    {layout}
    folders={$foldersStore}
    showFolders={$selectedFolderStore==='__ALL__' || $selectedFolderStore==='__UNFILED__'}
    selectedFolder={$selectedFolderStore}
    on:toggle={onToggleExpand}
    on:copy={(e) => { try { onCopy(e); } finally { toastMessage = 'Copied to clipboard'; showToast = true; setTimeout(() => (showToast = false), 1600); } }}
    on:delete={async (e) => { try { await deleteOneAction(e.detail); toastMessage = 'Deleted note'; showToast = true; setTimeout(() => (showToast = false), 1600); } catch (err) { console.error('Delete failed', err); toastMessage = 'Delete failed'; showToast = true; setTimeout(() => (showToast = false), 2000); } }}
    on:select={onSelectHandler}
    on:moveToFolder={onMoveToFolder}
    on:createFolder={onCreateFolder}
    on:createFolderAndMove={onCreateFolderAndMove}
    on:deleteFolder={(e) => {
      const nm = e.detail.name as string;
      const f = $foldersStore.find((x) => x.name === nm);
      dfName = nm; dfCount = f ? f.count : 0; dfOpen = true;
    }}
    on:openFolder={(e) => { folderActions.select(e.detail.name); }}
    on:navAll={() => { folderActions.selectAll(); }}
  />

  <BulkActions
    selectedCount={$selectedNotesStore.size}
    isDeleting={isDeleting}
    folders={$foldersStore.map(f=>f.name)}
    on:deleteSelected={async ()=>{ try { isDeleting = true; const count = $selectedNotesStore.size; await deleteManyAction(Array.from($selectedNotesStore)); notesActions.clearSelection(); lastSelectedIndex=null; toastMessage = count === 1 ? 'Deleted 1 note' : `Deleted ${count} notes`; showToast = true; setTimeout(() => (showToast = false), 1600); } catch (err) { console.error('Bulk delete failed', err); toastMessage = 'Bulk delete failed'; showToast = true; setTimeout(() => (showToast = false), 2000); } finally { isDeleting = false; } }}
    on:createNarrative={createNarrative}
    on:selectAll={() => { selectedNotesStore.set(new Set((filteredNotes||[]).map((n) => n.filename))); }}
    on:clearSelection={() => { notesActions.clearSelection(); lastSelectedIndex = null; }}
    on:bulkMove={async (e) => { const filenames = Array.from($selectedNotesStore); if (!filenames.length) return; await moveToFolderAction(e.detail.folder, filenames); notesActions.clearSelection(); }}
  />
</main>

<FormatsManager open={isFormatsOpen} on:close={() => (isFormatsOpen = false)} />
<TextNoteModal
  open={isTextNoteOpen}
  on:close={() => (isTextNoteOpen = false)}
  on:create={async (e) => {
    try {
      const { title, transcription, folder } = e.detail as { title?: string; transcription: string; folder?: string };
      await api.createTextNote({ title, transcription, folder });
      isTextNoteOpen = false;
      await refreshAll();
      toastMessage = 'Text note created';
      showToast = true; setTimeout(() => (showToast = false), 1600);
    } catch (err) {
      console.error('create text note failed', err);
      toastMessage = 'Failed to create text note';
      showToast = true; setTimeout(() => (showToast = false), 2000);
    }
  }}
/>
  <NarrativeGenerateModal
    open={isNarrativeModalOpen}
    selected={Array.from($selectedNotesStore)}
    loading={isGeneratingNarrative}
    on:close={() => (isNarrativeModalOpen = false)}
    on:generate={submitNarrativeGeneration}
  />

<DeleteFolderModal
  open={dfOpen}
  name={dfName}
  count={dfCount}
  on:close={() => { dfOpen=false; }}
  on:confirm={async () => {
    try {
      await appActions.deleteFolder(dfName);
      dfOpen=false; dfName=''; dfCount=0;
      // After deletion, go to Unfiled
      folderActions.selectUnfiled();
      await refreshAll();
    } catch (err) { console.error('Delete folder failed', err); }
  }}
/>

<style>
  .page { font-family: sans-serif; width: 100%; padding: 1rem 2rem; box-sizing: border-box; }
  @media (max-width: 900px) { .page { padding: 1rem; } }
  .loading-indicator { background-color: #f0f0f0; padding: 1rem; margin-bottom: 1rem; border-radius: 5px; text-align: center; }
  .bulk-upload-indicator { background-color: #f0f0f0; padding: 0.75rem 1rem; margin-bottom: 1rem; border-radius: 5px; text-align: center; }
  .progress { height: 8px; background:#e5e7eb; border-radius: 9999px; margin-top: 8px; overflow:hidden; }
  .bar { height: 100%; background:#3B82F6; width: 0; transition: width 0.2s ease; }
</style>
