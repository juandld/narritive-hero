<script lang="ts">
  import { onMount } from 'svelte';
  import Toast from '../lib/components/Toast.svelte';
  import RecordingControls from '../lib/components/RecordingControls.svelte';
  import PlacePrompt from '../lib/components/PlacePrompt.svelte';
  import NotesList from '../lib/components/NotesList.svelte';
  import FileUpload from '../lib/components/FileUpload.svelte';
  import NarrativesDrawer from '../lib/components/NarrativesDrawer.svelte';

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

  let includeDate: boolean = true;
  let includePlace: boolean = false;
  let detectedPlace: string = '';
  let showPlacePrompt: boolean = false;

  import { BACKEND_URL } from '../lib/config';

  // Filters moved to FiltersBar component
  import FiltersBar, { type Filters } from '../lib/components/FiltersBar.svelte';
  import BulkActions from '../lib/components/BulkActions.svelte';
  let filters: Filters = { dateFrom: '', dateTo: '', topics: '', minLen: '', maxLen: '', search: '' };

  function applyFilters() {
    const from = filters.dateFrom ? new Date(filters.dateFrom) : null;
    const to = filters.dateTo ? new Date(filters.dateTo) : null;
    const topicTokens = filters.topics
      .toLowerCase()
      .split(/[ ,]+/)
      .map((t) => t.trim())
      .filter(Boolean);
    const minLen = typeof filters.minLen === 'number' ? filters.minLen : null;
    const maxLen = typeof filters.maxLen === 'number' ? filters.maxLen : null;
    const q = filters.search.trim().toLowerCase();

    filteredNotes = notes.filter((n) => {
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
      if (minLen !== null && (n.length_seconds ?? 0) < minLen) return false;
      if (maxLen !== null && (n.length_seconds ?? 0) > maxLen) return false;
      // Text search across title + transcription
      if (q) {
        const hay = `${n.title ?? ''} ${n.transcription ?? ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
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

  function handleSelectNote(event: CustomEvent<{ filename: string; selected: boolean }>) {
    const { filename, selected } = event.detail;
    if (selected) {
      selectedNotes.add(filename);
    } else {
      selectedNotes.delete(filename);
    }
    selectedNotes = new Set(selectedNotes);
  }

  async function createNarrative() {
    const selectedNotesArray = Array.from(selectedNotes).map((filename) => ({
      filename
    }));

    try {
      const response = await fetch(`${BACKEND_URL}/api/narratives`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(selectedNotesArray)
      });

      if (response.ok) {
        toastMessage = 'Narrative created successfully!';
        showToast = true;
        setTimeout(() => {
          showToast = false;
        }, 3000);
        selectedNotes.clear();
        selectedNotes = new Set(selectedNotes);
        isNarrativesDrawerOpen = true; // Open the drawer to show the new narrative
      } else {
        console.error('Failed to create narrative');
        toastMessage = 'Failed to create narrative.';
        showToast = true;
        setTimeout(() => {
          showToast = false;
        }, 3000);
      }
    } catch (error) {
      console.error('Error creating narrative:', error);
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

<main style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 2rem;">
  <Toast message={toastMessage} show={showToast} />

  <h1 style="text-align: center;">Narrative Hero</h1>

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

  <FiltersBar bind:filters on:change={(e) => { filters = e.detail; applyFilters(); }} counts={{ total: notes.length, filtered: filteredNotes.length }} />
  <!-- legacy filters markup removed -->

  <NotesList
    notes={filteredNotes}
    {expandedNotes}
    {selectedNotes}
    on:toggle={(e) => toggleExpand(e.detail)}
    on:copy={(e) => copyToClipboard(e.detail)}
    on:delete={(e) => deleteNote(e.detail)}
    on:select={handleSelectNote}
  />

  <BulkActions selectedCount={selectedNotes.size} {isBulkDeleting} on:deleteSelected={deleteSelectedNotes} on:createNarrative={createNarrative} />
</main>

<NarrativesDrawer isOpen={isNarrativesDrawerOpen} onClose={() => (isNarrativesDrawerOpen = false)} />

<style>
  main {
    font-family: sans-serif;
    max-width: 600px;
    margin: auto;
    padding: 2rem;
  }

  .controls-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

  /* Filters moved to FiltersBar component */
</style>
