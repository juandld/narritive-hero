<script lang="ts">
  import { onMount } from 'svelte';

  // --- Types ---
  type Note = {
    filename: string;
    transcription?: string;
    title?: string;
  };

  // --- State ---
  let isRecording = false;
  let mediaRecorder: MediaRecorder | null = null;
  let audioChunks: Blob[] = [];
  let notes: Note[] = [];
  let expandedNotes = new Set<string>();
  let toastMessage = '';
  let showToast = false;
  let includeDate = true;
  let includePlace = false;
  let detectedPlace = '';
  let showPlacePrompt = false;
  let dragActive = false;
  let uploadFileInput: HTMLInputElement | null = null;

  const BACKEND_URL = 'https://voice.camofiles.app';

  // --- Utility Functions ---
  function showToastMsg(msg: string) {
    toastMessage = msg;
    showToast = true;
    setTimeout(() => showToast = false, 3000);
  }

  function toggleExpand(filename: string) {
    expandedNotes.has(filename) ? expandedNotes.delete(filename) : expandedNotes.add(filename);
    expandedNotes = new Set(expandedNotes); // Svelte reactivity
  }

  function getDisplayedTranscription(transcription?: string, filename?: string) {
    return expandedNotes.has(filename!) ? transcription ?? '' : '';
  }

  async function copyToClipboard(text?: string) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      showToastMsg('Transcription copied to clipboard!');
    } catch {
      showToastMsg('Failed to copy transcription.');
    }
  }

  // --- Location ---
  async function getLocationFallback(): Promise<string> {
    try {
      const response = await fetch('https://ipinfo.io/json?token=YOUR_TOKEN');
      const data = await response.json();
      return data.city ? `${data.city}, ${data.region}, ${data.country}` : 'Unknown location';
    } catch {
      return 'Unknown location';
    }
  }

  async function getLocation(): Promise<string> {
    return new Promise((resolve, reject) => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          pos => resolve(`Lat: ${pos.coords.latitude}, Lon: ${pos.coords.longitude}`),
          async err => {
            if (err.code === 2) return resolve(await getLocationFallback());
            reject(new Error('Could not get your location.'));
          }
        );
      } else {
        reject(new Error('Geolocation is not supported.'));
      }
    });
  }

  // --- Notes API ---
  async function getNotes() {
    try {
      const response = await fetch(`${BACKEND_URL}/api/notes`);
      notes = response.ok ? await response.json() : [];
    } catch {
      notes = [];
    }
  }

  async function deleteNote(filename: string) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/notes/${filename}`, { method: 'DELETE' });
      if (response.ok) await getNotes();
    } catch {}
  }

  // --- Recording ---
  async function startRecording() {
    if (includePlace) {
      try {
        detectedPlace = await getLocation();
        showPlacePrompt = true;
      } catch (error) {
        showToastMsg(error instanceof Error ? error.message : 'Location error');
      }
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
      mediaRecorder.onstop = async () => {
        await uploadRecording(new Blob(audioChunks, { type: 'audio/wav' }));
        audioChunks = [];
      };
      mediaRecorder.start();
      isRecording = true;
    } catch {
      showToastMsg('Could not access microphone.');
    }
  }

  function stopRecording() {
    mediaRecorder?.stop();
    isRecording = false;
  }

  async function uploadRecording(blob: Blob) {
    await uploadFile(blob, 'recording.wav');
  }

  // --- Upload ---
  async function uploadFile(file: Blob | File, filename?: string) {
    const formData = new FormData();
    formData.append('file', file, filename ?? (file as File).name);
    if (includeDate) formData.append('date', new Date().toISOString().split('T')[0]);
    if (includePlace && detectedPlace) formData.append('place', detectedPlace);

    try {
      const response = await fetch(`${BACKEND_URL}/api/notes`, { method: 'POST', body: formData });
      if (response.ok) {
        showToastMsg('Audio file uploaded!');
        await getNotes();
      } else {
        showToastMsg('Failed to upload audio file.');
      }
    } catch {
      showToastMsg('Error uploading audio file.');
    } finally {
      if (uploadFileInput) uploadFileInput.value = '';
    }
  }

  function handleFileUpload(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) uploadFile(input.files[0]);
  }

  function handleDrop(event: DragEvent) {
    dragActive = false;
    if (event.dataTransfer?.files?.length) uploadFile(event.dataTransfer.files[0]);
  }

  onMount(getNotes);
</script>

<main style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 2rem;">
  {#if showToast}
    <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #333; color: #fff; padding: 1rem 2rem; border-radius: 8px; z-index: 1000;">
      {toastMessage}
    </div>
  {/if}

  <h1 style="text-align: center;">Narrative Hero</h1>

  <!-- Options -->
  <div style="margin-bottom: 2rem; text-align: center;">
    <label><input type="checkbox" bind:checked={includeDate}> Include Date</label>
    <label style="margin-left: 2rem;"><input type="checkbox" bind:checked={includePlace}> Include Place</label>
    <div style="margin-top: 1rem;">
      {#if isRecording}
        <button on:click={stopRecording} style="background: #db4437; color: #fff; padding: 1rem 2rem; border: none; border-radius: 5px;">Stop Recording</button>
      {:else}
        <button on:click={startRecording} style="background: #4285f4; color: #fff; padding: 1rem 2rem; border: none; border-radius: 5px;">Start Recording</button>
      {/if}
    </div>
  </div>

  <!-- Location Prompt -->
  {#if showPlacePrompt}
    <div style="margin-top: 1rem; padding: 1rem; background: #e6f7ff; border: 1px solid #91d5ff; border-radius: 8px; text-align: center;">
      <p>Detected your location: {detectedPlace}. Do you want to add this to the note?</p>
      <button on:click={() => { includePlace = true; showPlacePrompt = false; }} style="background: #52c41a; color: #fff; padding: 0.5rem 1rem; border: none; border-radius: 4px; margin-right: 10px;">Yes</button>
      <button on:click={() => { includePlace = false; showPlacePrompt = false; }} style="background: #f5222d; color: #fff; padding: 0.5rem 1rem; border: none; border-radius: 4px;">No</button>
    </div>
  {/if}

  <!-- Drag-and-drop & click-to-upload -->
  <div
    on:dragover|preventDefault={() => dragActive = true}
    on:dragleave|preventDefault={() => dragActive = false}
    on:drop|preventDefault={handleDrop}
    on:click={() => uploadFileInput && uploadFileInput.click()}
    style="border: 2px dashed #4285f4; border-radius: 8px; padding: 2rem; text-align: center; background: {dragActive ? '#e3f2fd' : '#fafafa'}; cursor: pointer; margin-bottom: 1rem;"
  >
    <p style="margin: 0;">
      <strong>Drag & drop audio files here</strong><br>
      <span style="font-size: 0.9em;">or click to select files</span>
    </p>
    <input
      id="audio-upload"
      type="file"
      accept=".wav,.mp3,.m4a,.ogg,.flac"
      bind:this={uploadFileInput}
      on:change={handleFileUpload}
      style="display: none;"
    />
  </div>

  <!-- Notes List -->
  <h2>Saved Notes</h2>
  {#if notes.length}
    <ul style="list-style: none; padding: 0;">
      {#each notes as note}
        <li style="margin-bottom: 1.5rem; padding: 1rem; background: #f1f3f4; border-radius: 8px;">
          {#if note.title}
            <p><strong>Title:</strong> {note.title}</p>
          {/if}
          <audio controls src="{`${BACKEND_URL}/voice_notes/${note.filename}`}" style="width: 100%; margin-bottom: 0.5rem;"></audio>
          <blockquote style="background: #fff; padding: 0.5rem 1rem; border-left: 5px solid #4285f4; margin: 0;">
            <p>{getDisplayedTranscription(note.transcription, note.filename)}</p>
            {#if note.transcription}
              <button on:click={() => toggleExpand(note.filename)} style="background: none; border: none; color: #4285f4; cursor: pointer; font-size: 0.9em;">
                {expandedNotes.has(note.filename) ? '\u25B2' : '\u25BC'}
              </button>
            {/if}
          </blockquote>
          <button on:click={() => copyToClipboard(note.transcription)} style="background: #4285f4; color: #fff; padding: 0.5rem 1rem; border: none; border-radius: 4px; margin-top: 10px;">Copy TS</button>
          <button on:click={() => deleteNote(note.filename)} style="background: #db4437; color: #fff; padding: 0.5rem 1rem; border: none; border-radius: 4px; margin-top: 10px; margin-left: 10px;">Delete</button>
        </li>
      {/each}
    </ul>
  {:else}
    <p>No notes found. Record or upload one above!</p>
  {/if}
</main>

