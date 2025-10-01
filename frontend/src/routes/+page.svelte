<script lang="ts">
  import { onMount } from 'svelte';
  import Toast from '../lib/components/Toast.svelte';
  import RecordingControls from '../lib/components/RecordingControls.svelte';
  import PlacePrompt from '../lib/components/PlacePrompt.svelte';
  import NotesList from '../lib/components/NotesList.svelte';
  import FileUpload from '../lib/components/FileUpload.svelte';
  import NarrativesDrawer from '../lib/components/NarrativesDrawer.svelte';
  import NarrativeGenerateModal from '../lib/components/NarrativeGenerateModal.svelte';
  import FormatsManager from '../lib/components/FormatsManager.svelte';

  type Note = {
    filename: string;
    transcription?: string;
    title?: string;
    date?: string; // YYYY-MM-DD
    length_seconds?: number;
    topics?: string[];
  };

  let isRecording = false;
  let mediaRecorder: MediaRecorder | null = null;
  let audioChunks: Blob[] = [];
  let notes: Note[] = [];
  let filteredNotes: Note[] = [];
  let expandedNotes: Set<string> = new Set();
  let selectedNotes: Set<string> = new Set();
  let toastMessage = '';
  let showToast = false;
  let isUploading = false;
  let isBulkDeleting = false;
  // Multi-file upload progress
  let multiUploadActive = false;
  let multiUploadTotal = 0;
  let multiUploadIndex = 0;
  $: multiUploadPercent = multiUploadTotal ? Math.floor((multiUploadIndex / multiUploadTotal) * 100) : 0;

  let isNarrativesDrawerOpen = false;
  let initialNarrativeSelect: string | null = null;
  let isNarrativeModalOpen = false;
  let isGeneratingNarrative = false;
  let isFormatsOpen = false;

  let includeDate: boolean = true;
  let includePlace: boolean = false;
  let detectedPlace: string = '';
  let showPlacePrompt: boolean = false;

  import { BACKEND_URL } from '../lib/config';

  // Filters moved to FiltersBar component
  import FiltersBar, { type Filters } from '../lib/components/FiltersBar.svelte';
  import BulkActions from '../lib/components/BulkActions.svelte';
  let filters: Filters = { dateFrom: '', dateTo: '', topics: '', minLen: '', maxLen: '', search: '' };
  let layout: 'list' | 'compact' | 'grid3' = 'list';
  // Client-side duration cache for notes missing length_seconds
  let computedDurations: Record<string, number> = {};

  async function loadDurationFor(filename: string): Promise<number | null> {
    return new Promise((resolve) => {
      try {
        const audio = new Audio();
        audio.preload = 'metadata';
        audio.src = `${BACKEND_URL}/voice_notes/${filename}`;
        const cleanup = () => {
          audio.onloadedmetadata = null;
          audio.onerror = null;
        };
        audio.onloadedmetadata = () => {
          const dur = Number.isFinite(audio.duration) ? Math.round(audio.duration * 100) / 100 : NaN;
          cleanup();
          resolve(Number.isFinite(dur) ? dur : null);
        };
        audio.onerror = () => { cleanup(); resolve(null); };
      } catch (e) {
        resolve(null);
      }
    });
  }

  async function ensureDurations() {
    const targets = notes.filter((n) => n && n.filename && (n.length_seconds == null) && !(n.filename in computedDurations));
    for (const n of targets) {
      const d = await loadDurationFor(n.filename);
      if (d != null) {
        computedDurations[n.filename] = d;
      }
    }
    applyFilters();
  }

  function applyFilters() {
    const from = filters.dateFrom ? new Date(filters.dateFrom) : null;
    const to = filters.dateTo ? new Date(filters.dateTo) : null;
    const topicTokens = filters.topics
      .toLowerCase()
      .split(/[ ,]+/)
      .map((t) => t.trim())
      .filter(Boolean);
    const minLen = typeof filters.minLen === 'number' && Number.isFinite(filters.minLen) ? filters.minLen : null;
    const maxLen = typeof filters.maxLen === 'number' && Number.isFinite(filters.maxLen) ? filters.maxLen : null;
    const q = filters.search.trim().toLowerCase();

    console.log('[applyFilters] filters', filters);
    filteredNotes = notes.filter((n) => {
      let len: number | null = null;
      if (typeof n.length_seconds === 'number' && Number.isFinite(n.length_seconds)) {
        len = n.length_seconds;
      } else if (typeof n.length_seconds === 'string') {
        const parsed = Number(n.length_seconds);
        if (Number.isFinite(parsed)) len = parsed;
      }
      if (len == null && computedDurations[n.filename] != null) {
        len = computedDurations[n.filename];
      }
      // Date filter
      if (from || to) {
        if (!n.date) return false;
        const d = new Date(n.date);
        if (from && d < from) return false;
        if (to) {
          const end = new Date(to);
          end.setHours(23, 59, 59, 999);
          if (d > end) return false;
        }
      }
      // Topics filter (any match)
      if (topicTokens.length) {
        const noteTopics = (n.topics || []).map((t) => t.toLowerCase());
        const hasAny = topicTokens.some((t) => noteTopics.includes(t));
        if (!hasAny) return false;
      }
      // Length filter
      const passLen = !((minLen !== null && len !== null && len < minLen) || (maxLen !== null && len !== null && len > maxLen));
      if (!passLen) {
        console.log('[applyFilters] drop by length', { file: n.filename, raw: n.length_seconds, len, minLen, maxLen });
        return false;
      }
      // Text search across title + transcription
      if (q) {
        const hay = `${n.title ?? ''} ${n.transcription ?? ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      const keep = true;
      if (!keep) {
        console.log('[applyFilters] drop by other filter', { file: n.filename });
      } else {
        console.log('[applyFilters] keep', { file: n.filename, len, date: n.date, topics: n.topics });
      }
      return keep;
    });
    console.log('[applyFilters] result', { total: notes.length, filtered: filteredNotes.length });
  }

  // Reset handled by FiltersBar

  function toggleExpand(filename: string) {
    if (expandedNotes.has(filename)) {
      expandedNotes.delete(filename);
    } else {
      expandedNotes.add(filename);
    }
    expandedNotes = new Set(expandedNotes); // Fix: Trigger Svelte reactivity
  }

  let lastSelectedIndex: number | null = null;
  function handleSelectNote(event: CustomEvent<{ filename: string; selected: boolean; index: number; shift?: boolean }>) {
    const { filename, selected, index, shift } = event.detail;
    const inRangeSelect = (idx: number, state: boolean) => {
      const fn = filteredNotes[idx]?.filename;
      if (!fn) return;
      if (state) selectedNotes.add(fn); else selectedNotes.delete(fn);
    };
    if (shift && lastSelectedIndex !== null && filteredNotes.length > 0) {
      const start = Math.max(0, Math.min(lastSelectedIndex, index));
      const end = Math.min(filteredNotes.length - 1, Math.max(lastSelectedIndex, index));
      for (let i = start; i <= end; i++) inRangeSelect(i, selected);
    } else {
      inRangeSelect(index, selected);
    }
    selectedNotes = new Set(selectedNotes);
    // Update anchor only on non-shift clicks (common UX)
    if (!shift) lastSelectedIndex = index;
  }

  function createNarrative() {
    isNarrativeModalOpen = true;
  }

  async function submitNarrativeGeneration(e: CustomEvent<{ extra_text: string; provider: string; model: string; temperature: number; format_ids?: string[] }>) {
    const selectedNotesArray = Array.from(selectedNotes).map((filename) => ({ filename }));
    const { extra_text, provider, model, temperature, format_ids } = e.detail;
    try {
      isGeneratingNarrative = true;
      const response = await fetch(`${BACKEND_URL}/api/narratives/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: selectedNotesArray, extra_text, provider, model: model || undefined, temperature, format_ids })
      });
      if (response.ok) {
        const data = await response.json();
        const fname = data?.filename as string | undefined;
        toastMessage = 'Narrative created successfully!';
        showToast = true;
        setTimeout(() => { showToast = false; }, 3000);
        selectedNotes.clear();
        selectedNotes = new Set(selectedNotes);
        initialNarrativeSelect = fname || null;
        isNarrativesDrawerOpen = true;
        isNarrativeModalOpen = false;
      } else {
        console.error('Failed to create narrative');
        toastMessage = 'Failed to create narrative.';
        showToast = true;
        setTimeout(() => { showToast = false; }, 3000);
      }
    } catch (error) {
      console.error('Error creating narrative:', error);
      toastMessage = 'Error creating narrative.';
      showToast = true;
      setTimeout(() => { showToast = false; }, 3000);
    } finally {
      isGeneratingNarrative = false;
    }
  }

  function getLocation(): Promise<string> {
    return new Promise((resolve, reject) => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const place = `Lat: ${position.coords.latitude}, Lon: ${position.coords.longitude}`;
            resolve(place);
          },
          (error) => {
            console.error('Error getting location:', error);
            reject(new Error('Could not get your location.'));
          }
        );
      } else {
        reject(new Error('Geolocation is not supported by this browser.'));
      }
    });
  }

  async function getNotes() {
    try {
      const response = await fetch(`${BACKEND_URL}/api/notes`);
      if (response.ok) {
        notes = await response.json();
        applyFilters();
        // Fill missing durations in the background for better filtering UX
        ensureDurations();
      } else {
        console.error('Failed to fetch notes:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to fetch notes:', error);
    }
  }

  async function copyToClipboard(text: string | undefined) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      toastMessage = 'Transcription copied to clipboard!';
      showToast = true;
      setTimeout(() => {
        showToast = false;
      }, 3000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
      toastMessage = 'Failed to copy transcription.';
      showToast = true;
      setTimeout(() => {
        showToast = false;
      }, 3000);
    }
  }

  async function startRecording() {
    try {
      if (includePlace) {
        try {
          detectedPlace = await getLocation();
          showPlacePrompt = true;
        } catch (error) {
          console.error(error);
          toastMessage =
            typeof error === 'object' && error !== null && 'message' in error
              ? String((error as { message: unknown }).message)
              : 'An error occurred';
          showToast = true;
          setTimeout(() => {
            showToast = false;
          }, 3000);
        }
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        audioChunks = [];
        await uploadRecording(audioBlob);
      };
      mediaRecorder.start();
      isRecording = true;
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone. Please ensure you have given permission.');
    }
  }

  function stopRecording() {
    if (mediaRecorder) {
      mediaRecorder.stop();
      isRecording = false;
    }
  }

  async function uploadRecording(blob: Blob, skipPoll: boolean = false) {
    const formData = new FormData();
    formData.append('file', blob, 'recording.wav');
    if (includeDate) {
      const currentDate = new Date().toISOString().split('T')[0];
      formData.append('date', currentDate);
    }
    if (includePlace && detectedPlace) formData.append('place', detectedPlace);

    isUploading = true;
    try {
      const response = await fetch(`${BACKEND_URL}/api/notes`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const newNote = await response.json();
        console.log('Upload successful, starting to poll for transcription for', newNote.filename);
        if (skipPoll) {
          // Quick refresh only; batch handler will keep refreshing the list
          await getNotes();
        } else {
          // Poll for transcription
          const poll = async () => {
            await getNotes();
            const note = notes.find((n) => n.filename === newNote.filename);

            // Stop polling if the transcription is present (either success or a failure message)
            if (note && note.transcription) {
              isUploading = false;
              if (note.transcription === 'Transcription failed.') {
                console.error('Transcription failed for', newNote.filename);
                toastMessage = 'Transcription failed. Please try again.';
                showToast = true;
                setTimeout(() => {
                  showToast = false;
                }, 3000);
              } else {
                console.log('Transcription complete for', newNote.filename);
              }
            } else {
              // If transcription is not yet present, poll again
              setTimeout(poll, 2000);
            }
          };
          poll();
        }
      } else {
        console.error('Upload failed');
        isUploading = false;
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      isUploading = false;
    }
  }

  onMount(() => {
    getNotes();
  });

  async function deleteNote(filename: string) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/notes/${filename}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        console.log('Delete successful');
        await getNotes(); // Refresh the list
      } else {
        console.error('Delete failed');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
    }
  }

  async function deleteSelectedNotes() {
    if (selectedNotes.size === 0) return;
    const confirmed = window.confirm(
      `Delete ${selectedNotes.size} selected note(s)? This removes audio, transcription, and title files.`
    );
    if (!confirmed) return;
    isBulkDeleting = true;
    try {
      const filenames = Array.from(selectedNotes);
      const results = await Promise.allSettled(
        filenames.map((filename) =>
          fetch(`${BACKEND_URL}/api/notes/${filename}`, { method: 'DELETE' })
        )
      );
      const successCount = results.filter(
        (r) => r.status === 'fulfilled' && (r as PromiseFulfilledResult<Response>).value.ok
      ).length;
      const failCount = results.length - successCount;
      await getNotes();
      selectedNotes.clear();
      selectedNotes = new Set(selectedNotes);
      toastMessage = `Deleted ${successCount} note(s)` + (failCount ? `, ${failCount} failed` : '');
      showToast = true;
      setTimeout(() => {
        showToast = false;
      }, 3000);
    } catch (error) {
      console.error('Bulk delete error:', error);
      toastMessage = 'Failed to delete selected notes.';
      showToast = true;
      setTimeout(() => {
        showToast = false;
      }, 3000);
    } finally {
      isBulkDeleting = false;
    }
  }

  function handlePlacePromptResponse(event: CustomEvent<boolean>) {
    includePlace = event.detail;
    showPlacePrompt = false;
  }

  async function handleFileSelected(event: CustomEvent<File>) {
    const file = event.detail;
    await uploadRecording(file);
  }
  // Periodic refresh window for batch uploads
  let batchRefreshTimer: number | null = null;
  function startBatchRefreshWindow(ms = 30000) {
    if (batchRefreshTimer) {
      clearInterval(batchRefreshTimer);
      batchRefreshTimer = null;
    }
    const started = Date.now();
    batchRefreshTimer = setInterval(async () => {
      await getNotes();
      if (Date.now() - started > ms) {
        if (batchRefreshTimer) clearInterval(batchRefreshTimer);
        batchRefreshTimer = null;
      }
    }, 2000) as unknown as number;
  }

</script>

<main class="page">
  <Toast message={toastMessage} show={showToast} />

  <h1 class="title">Narrative Hero</h1>

  <div class="controls-container">
    <FileUpload on:files-selected={async (e) => {
      const files: File[] = e.detail;
      if (!files || files.length === 0) return;
      multiUploadActive = true;
      multiUploadTotal = files.length;
      multiUploadIndex = 0;
      for (const f of files) {
        multiUploadIndex += 1;
        await uploadRecording(f, true);
      }
      startBatchRefreshWindow(30000);
      // slight delay to let the last polling settle
      setTimeout(() => {
        multiUploadActive = false;
        multiUploadTotal = 0;
        multiUploadIndex = 0;
      }, 300);
    }} />
    <button class="narrative-button" on:click={() => (isNarrativesDrawerOpen = true)}>View Narratives</button>
    <button class="narrative-button" on:click={() => (isFormatsOpen = true)}>Formats</button>
  </div>

  <RecordingControls
    bind:isRecording
    bind:includeDate
    bind:includePlace
    {startRecording}
    {stopRecording}
  />

  {#if showPlacePrompt}
    <PlacePrompt {detectedPlace} on:response={handlePlacePromptResponse} />
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
    {filters}
    on:change={(e) => {
      console.log('[Page] Filters change', e.detail);
      filters = e.detail;
      applyFilters();
    }}
    on:selectAll={() => {
      selectedNotes = new Set(filteredNotes.map((n) => n.filename));
    }}
    on:clearSelection={() => {
      selectedNotes.clear();
      selectedNotes = new Set(selectedNotes);
      lastSelectedIndex = null;
    }}
    counts={{ total: notes.length, filtered: filteredNotes.length }}
  />
  <!-- legacy filters markup removed -->

  <div class="view-toggle">
    <label>View:</label>
    <div class="seg">
      <button class:active={layout==='list'} on:click={() => (layout='list')}>List</button>
      <button class:active={layout==='compact'} on:click={() => (layout='compact')}>Compact</button>
      <button class:active={layout==='grid3'} on:click={() => (layout='grid3')}>Grid x3</button>
    </div>
  </div>

  <NotesList
    notes={filteredNotes}
    {expandedNotes}
    {selectedNotes}
    {layout}
    on:toggle={(e) => toggleExpand(e.detail)}
    on:copy={(e) => copyToClipboard(e.detail)}
    on:delete={(e) => deleteNote(e.detail)}
    on:select={handleSelectNote}
  />

  <BulkActions
    selectedCount={selectedNotes.size}
    {isBulkDeleting}
    on:deleteSelected={deleteSelectedNotes}
    on:createNarrative={createNarrative}
    on:selectAll={() => { selectedNotes = new Set(filteredNotes.map((n) => n.filename)); }}
    on:clearSelection={() => { selectedNotes.clear(); selectedNotes = new Set(selectedNotes); lastSelectedIndex = null; }}
  />
</main>

<NarrativesDrawer isOpen={isNarrativesDrawerOpen} initialSelect={initialNarrativeSelect} onClose={() => (isNarrativesDrawerOpen = false)} />
<FormatsManager open={isFormatsOpen} on:close={() => (isFormatsOpen = false)} />
<NarrativeGenerateModal
  open={isNarrativeModalOpen}
  selected={Array.from(selectedNotes)}
  loading={isGeneratingNarrative}
  on:close={() => (isNarrativeModalOpen = false)}
  on:generate={submitNarrativeGeneration}
/>

<style>
  .page {
    font-family: sans-serif;
    width: 100%;
    padding: 1rem 2rem;
    box-sizing: border-box;
  }
  @media (max-width: 900px) { .page { padding: 1rem; } }
  .title { margin: 0 0 1rem 0; font-size: 1.6rem; font-weight: 700; }

  .controls-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: .75rem;
    margin-bottom: 1rem;
  }

  .narrative-button {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
  }

  .loading-indicator {
    background-color: #f0f0f0;
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 5px;
    text-align: center;
  }
  .bulk-upload-indicator {
    background-color: #f0f0f0;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    border-radius: 5px;
    text-align: center;
  }
  .progress { height: 8px; background:#e5e7eb; border-radius: 9999px; margin-top: 8px; overflow:hidden; }
  .bar { height: 100%; background:#3B82F6; width: 0; transition: width 0.2s ease; }

  .view-toggle { display:flex; align-items:center; gap:.5rem; margin: .5rem 0 1rem 0; }
  .view-toggle .seg { display:inline-flex; border:1px solid #e5e7eb; border-radius: 8px; overflow:hidden; }
  .view-toggle .seg button { border:none; padding:.35rem .6rem; background:#fff; cursor:pointer; }
  .view-toggle .seg button.active { background:#eef2ff; color:#4338ca; font-weight:600; }

  /* Filters moved to FiltersBar component */
</style>
