<script lang="ts">
  import { onMount } from 'svelte';

  type Note = {
    filename: string;
    transcription?: string;
    title?: string;
  };

  let isRecording = false;
  let mediaRecorder: MediaRecorder | null = null;
  let audioChunks: Blob[] = [];
  let notes: Note[] = [];
  let expandedNotes: Set<string> = new Set();
  let toastMessage = '';
  let showToast = false;

  let subject: string = '';
  let includeDate: boolean = true;
  let includePlace: boolean = false;
  let detectedPlace: string = '';
  let showPlacePrompt: boolean = false;

  const BACKEND_URL = 'http://localhost:8000';

  function toggleExpand(filename: string) {
    if (expandedNotes.has(filename)) {
      expandedNotes.delete(filename);
    } else {
      expandedNotes.add(filename);
    }
    expandedNotes = new Set(expandedNotes); // Fix: Trigger Svelte reactivity
  }

  function getDisplayedTranscription(transcription: string | undefined, filename: string): string {
    if (!transcription) return '';
    if (expandedNotes.has(filename)) {
      return transcription;
    } else {
      return ''; // No preview by default
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
          toastMessage = typeof error === 'object' && error !== null && 'message' in error ? String((error as { message: unknown }).message) : 'An error occurred';
          showToast = true;
          setTimeout(() => {
            showToast = false;
          }, 3000);
        }
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = event => {
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

  async function uploadRecording(blob: Blob) {
    const formData = new FormData();
    formData.append('file', blob, 'recording.wav');
    if (includeDate) {
      const currentDate = new Date().toISOString().split('T')[0];
      formData.append('date', currentDate);
    }
    if (includePlace && detectedPlace) formData.append('place', detectedPlace);

    try {
      const response = await fetch(`${BACKEND_URL}/api/notes`, {
        method: 'POST',
        body: formData
      });
      if (response.ok) {
        console.log('Upload successful');
        await getNotes(); // Refresh the list
      } else {
        console.error('Upload failed');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
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
</script>

<main style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 2rem;">
  {#if showToast}
    <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background-color: #333; color: white; padding: 1rem 2rem; border-radius: 8px; z-index: 1000; transition: opacity 0.5s ease;">
      {toastMessage}
    </div>
  {/if}

  <h1 style="text-align: center;">Narrative Hero</h1>

  <div style="margin-bottom: 2rem; text-align: center;">
    <div style="margin-bottom: 1rem; display: flex; align-items: center; justify-content: center;">
      <input type="checkbox" bind:checked={includeDate} id="includeDate" style="margin-right: 10px;">
      <label for="includeDate">Include Date</label>
    </div>
    <div style="margin-bottom: 1rem; display: flex; align-items: center; justify-content: center;">
      <input type="checkbox" bind:checked={includePlace} id="includePlace" style="margin-right: 10px;">
      <label for="includePlace">Include Place</label>
    </div>
    {#if isRecording}
      <button on:click={stopRecording} style="background-color: #db4437; color: white; padding: 1rem 2rem; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer;">
        Stop Recording
      </button>
    {:else}
      <button on:click={startRecording} style="background-color: #4285f4; color: white; padding: 1rem 2rem; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer;">
        Start Recording
      </button>
    {/if}
  </div>

  {#if showPlacePrompt}
    <div style="margin-top: 1rem; padding: 1rem; background-color: #e6f7ff; border: 1px solid #91d5ff; border-radius: 8px; text-align: center;">
      <p>Detected your location: {detectedPlace}. Do you want to add this to the note?</p>
      <button on:click={() => { includePlace = true; showPlacePrompt = false; }} style="background-color: #52c41a; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;">Yes</button>
      <button on:click={() => { includePlace = false; showPlacePrompt = false; }} style="background-color: #f5222d; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer;">No</button>
    </div>
  {/if}

  <h2>Saved Notes</h2>
  {#if notes.length > 0}
    <ul style="list-style: none; padding: 0;">
      {#each notes as note}
        <li style="margin-bottom: 1.5rem; padding: 1rem; background-color: #f1f3f4; border-radius: 8px;">
          {#if note.title}
            <p><strong>Title:</strong> {note.title}</p>
          {/if}
          <audio controls src="{`${BACKEND_URL}/voice_notes/${note.filename}`}" style="width: 100%; margin-bottom: 0.5rem;"></audio>
          <blockquote style="background-color: white; padding: 0.5rem 1rem; border-left: 5px solid #4285f4; margin: 0;">
            <p>{getDisplayedTranscription(note.transcription, note.filename)}</p>
            {#if note.transcription && note.transcription.length > 0}
              <button on:click={() => toggleExpand(note.filename)} style="background: none; border: none; color: #4285f4; cursor: pointer; font-size: 0.9em; transform: rotate({expandedNotes.has(note.filename) ? '180deg' : '0deg'});">
                {expandedNotes.has(note.filename) ? '\u25B2' : '\u25BC'}
              </button>
            {/if}
          </blockquote>
          <button on:click={() => copyToClipboard(note.transcription)} style="background-color: #4285f4; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px;">Copy TS</button>
          <button on:click={() => deleteNote(note.filename)} style="background-color: #db4437; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; margin-left: 10px;">Delete</button>
        </li>
      {/each}
    </ul>
  {:else}
    <p>No notes found. Record one above!</p>
  {/if}
</main>

