<script lang="ts">
  import { onMount } from 'svelte';
  import Toast from '../lib/components/Toast.svelte';
  import RecordingControls from '../lib/components/RecordingControls.svelte';
  import PlacePrompt from '../lib/components/PlacePrompt.svelte';
  import NotesList from '../lib/components/NotesList.svelte';
  import FileUpload from '../lib/components/FileUpload.svelte';

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

  function handlePlacePromptResponse(event: CustomEvent<boolean>) {
    includePlace = event.detail;
    showPlacePrompt = false;
  }

  async function handleFileSelected(event: CustomEvent<File>) {
    const file = event.detail;
    await uploadRecording(file);
  }
</script>

<main style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 2rem;">
  <Toast message={toastMessage} show={showToast} />

  <h1 style="text-align: center;">Narrative Hero</h1>

  <FileUpload on:file-selected={handleFileSelected} />

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

  <NotesList
    {notes}
    {expandedNotes}
    on:toggle={(e) => toggleExpand(e.detail)}
    on:copy={(e) => copyToClipboard(e.detail)}
    on:delete={(e) => deleteNote(e.detail)}
  />
</main>