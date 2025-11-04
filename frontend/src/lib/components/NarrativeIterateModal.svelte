<script lang="ts">
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { BACKEND_URL } from '../config';
  import AudioWaveform from 'svelte-audio-waveform';

  export let open: boolean = false;
  export let currentContent: string = '';
  export let selectedExcerpt: string = '';
  export let parentFilename: string = '';
  export let selectedNarratives: string[] = [];

  const dispatch = createEventDispatcher();

  type Note = { filename: string; title?: string; transcription?: string };
  let notes: Note[] = [];
  let loadingNotes = false;

  // Mode selection
  type Mode = 'note' | 'text' | 'record' | 'narratives';
  let mode: Mode = 'note';

  // Existing note selection
  let selectedNote: string = '';

  // Extra text
  let extraText: string = '';
  let errorMessage: string = '';
  let submitting = false;

  // Recording state
  let isRecording = false;
  let mediaRecorder: MediaRecorder | null = null;
  let audioChunks: Blob[] = [];
  let uploading = false;
  let newNoteFilename: string | null = null;
  let polling = false;
  let pollError: string = '';
  let mounted = false;

  // Live waveform visualization while recording
  const DEFAULT_WAVE_SAMPLES = 120;
  const WAVEFORM_HEIGHT = 84;
  let waveformPeaks: number[] = Array(DEFAULT_WAVE_SAMPLES).fill(0);
  let waveformAnimation: number | null = null;
  let audioContext: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let waveformDataArray: Uint8Array | null = null;
  let mediaStream: MediaStream | null = null;
  let mediaStreamSource: MediaStreamAudioSourceNode | null = null;
  let waveformContainer: HTMLDivElement | null = null;
  let waveformWidth = 320;

  // Selection scope for how to use the excerpt
  type Scope = 'whole' | 'focus' | 'section';
  let scope: Scope = 'whole';

  // Formats
  type Format = { id: string; title: string; prompt: string };
  let formats: Format[] = [];
  let format_ids: string[] = [];
  async function loadFormats(){ try{ const r = await fetch(`${BACKEND_URL}/api/formats`); if(r.ok) formats = await r.json(); }catch{} }
  $: if (open) loadFormats();

  async function fetchNotes() {
    loadingNotes = true;
    try {
      const res = await fetch(`${BACKEND_URL}/api/notes`);
      if (res.ok) {
        notes = await res.json();
      }
    } finally {
      loadingNotes = false;
    }
  }

  onMount(() => {
    mounted = true;
    if (open) fetchNotes();
  });

  $: if (open) {
    // Refresh notes when opening, but avoid spamming
    fetchNotes();
  }

  $: waveformWidth = waveformContainer?.clientWidth || 320;

  function close() {
    if (uploading || polling || isRecording) return;
    dispatch('close');
  }

  function stopVisualizer() {
    if (waveformAnimation !== null) {
      cancelAnimationFrame(waveformAnimation);
      waveformAnimation = null;
    }
    if (mediaStreamSource) {
      try {
        mediaStreamSource.disconnect();
      } catch (err) {
        console.debug('visualizer disconnect error', err);
      }
      mediaStreamSource = null;
    }
    if (audioContext) {
      const ctx = audioContext;
      audioContext = null;
      ctx.close().catch(() => {});
    }
    analyser = null;
    waveformDataArray = null;
    waveformPeaks = Array(DEFAULT_WAVE_SAMPLES).fill(0);
  }

  function clearStream() {
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (err) {
          console.debug('stream stop error', err);
        }
      });
      mediaStream = null;
    }
  }

  function startVisualizer(stream: MediaStream) {
    stopVisualizer();
    try {
      if (typeof window === 'undefined') return;
      const Ctx = (window.AudioContext || (window as any).webkitAudioContext) as typeof AudioContext;
      audioContext = new Ctx();
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 512;
      waveformDataArray = new Uint8Array(analyser.fftSize);
      mediaStreamSource = audioContext.createMediaStreamSource(stream);
      mediaStreamSource.connect(analyser);
      waveformPeaks = Array(DEFAULT_WAVE_SAMPLES).fill(0);

      const tick = () => {
        if (!analyser || !waveformDataArray) return;
        analyser.getByteTimeDomainData(waveformDataArray);
        let sum = 0;
        for (let i = 0; i < waveformDataArray.length; i++) {
          const deviation = waveformDataArray[i] - 128;
          sum += Math.abs(deviation);
        }
        const amplitude = Math.min(1, sum / (waveformDataArray.length * 128));
        waveformPeaks = [...waveformPeaks.slice(1), amplitude];
        waveformAnimation = requestAnimationFrame(tick);
      };
      waveformAnimation = requestAnimationFrame(tick);
    } catch (err) {
      console.error('visualizer init error', err);
      stopVisualizer();
    }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStream = stream;
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
      mediaRecorder.onstop = async () => {
        isRecording = false;
        const mime = (mediaRecorder && (mediaRecorder as any).mimeType) || (audioChunks[0] && (audioChunks[0] as any).type) || 'audio/webm';
        const blob = new Blob(audioChunks, { type: mime });
        audioChunks = [];
        stopVisualizer();
        clearStream();
        mediaRecorder = null;
        await uploadRecording(blob);
      };
      audioChunks = [];
      mediaRecorder.start();
      isRecording = true;
      startVisualizer(stream);
    } catch (e) {
      console.error('mic error', e);
      alert('Mic permission denied or unavailable.');
      mediaRecorder = null;
      mediaStream = null;
      stopVisualizer();
      clearStream();
    }
  }

  function stopRecording() {
    if (mediaRecorder) {
      mediaRecorder.stop();
      isRecording = false;
    }
    stopVisualizer();
    clearStream();
  }

  async function uploadRecording(blob: Blob) {
    uploading = true;
    pollError = '';
    newNoteFilename = null;
    try {
      const fd = new FormData();
      // Choose extension based on mime
      const mt = (blob as any).type || 'audio/webm';
      const ext = mt.includes('webm') ? 'webm' : mt.includes('ogg') ? 'ogg' : mt.includes('mp3') ? 'mp3' : mt.includes('mp4') ? 'm4a' : 'wav';
      fd.append('file', blob, `iterate.${ext}`);
      const res = await fetch(`${BACKEND_URL}/api/notes`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      newNoteFilename = data.filename;
      // Poll until transcription exists
      await pollForTranscription(newNoteFilename);
      // Once ready, set mode to note and selectedNote
      mode = 'note';
      selectedNote = newNoteFilename;
      await fetchNotes();
    } catch (e: any) {
      console.error('upload/poll error', e);
      pollError = e?.message || 'Upload or transcription failed.';
    } finally {
      uploading = false;
    }
  }

  async function pollForTranscription(filename: string) {
    polling = true;
    pollError = '';
    const started = Date.now();
    const timeoutMs = 120000; // 2 min
    try {
      while (Date.now() - started < timeoutMs) {
        const res = await fetch(`${BACKEND_URL}/api/notes`);
        if (res.ok) {
          const list: Note[] = await res.json();
          const n = list.find((x) => x.filename === filename);
          if (n && n.transcription && n.transcription !== 'Transcription failed.') {
            return;
          }
          if (n && n.transcription === 'Transcription failed.') {
            throw new Error('Transcription failed');
          }
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
      throw new Error('Timed out waiting for transcription');
    } finally {
      polling = false;
    }
  }

  $: canGenerate = (
    (mode === 'note' && (!!selectedNote || !!currentContent.trim())) ||
    (mode === 'text' && !!extraText.trim()) ||
    (mode === 'record' && !!newNoteFilename) ||
    (mode === 'narratives' && (selectedNarratives?.length || 0) > 0)
  );
  $: if (open && (selectedNarratives?.length || 0) > 0) { mode = 'narratives'; }

  async function submit() {
    if (uploading || polling || submitting) return;
    errorMessage = '';
    let items: { filename: string }[] = [];
    let extra = `Previous Narrative:\n\n${currentContent.trim()}`;
    if (mode === 'note') {
      if (selectedNote) {
        items = [{ filename: selectedNote }];
      }
      // If no selected note, proceed with just the previous narrative in extra
    } else if (mode === 'narratives') {
      if (!selectedNarratives || selectedNarratives.length === 0) return;
      items = selectedNarratives.map((fn) => ({ filename: fn }));
    } else if (mode === 'text') {
      if (!extraText.trim()) return;
      extra += `\n\nNew Input:\n\n${extraText.trim()}`;
    } else if (mode === 'record') {
      // If in record mode and finished upload, selectedNote will be set by uploader
      if (newNoteFilename) {
        items = [{ filename: newNoteFilename }];
      } else {
        return;
      }
    }
    // Selection-aware guidance
    let system: string | undefined = undefined;
    if (selectedExcerpt) {
      if (scope === 'focus') {
        extra += `\n\nFocus Excerpt:\n\n${selectedExcerpt}`;
        system = 'You are an expert editor. Produce a revised, cohesive narrative. Focus improvements around the provided excerpt, but adjust surrounding sections for clarity as needed. Keep structure tight and actionable.';
      } else if (scope === 'section') {
        extra += `\n\nSelected Excerpt To Update:\n\n${selectedExcerpt}`;
        system = 'You are an expert editor. Return a full revised narrative that changes ONLY the selected excerpt and minimal adjacent sentences to keep flow. Leave unrelated sections unchanged. Preserve headings and lists.';
      }
    }

    const body: any = { items, extra_text: extra, provider: 'auto', parent: parentFilename };
    if (format_ids && format_ids.length) body.format_ids = format_ids;
    if (system) body.system = system;
    try {
      submitting = true;
      dispatch('start');
      const res = await fetch(`${BACKEND_URL}/api/narratives/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (res.ok) {
        const data = await res.json();
        dispatch('done', { filename: data.filename });
      } else {
        const t = await res.text();
        errorMessage = `Failed to generate iteration (${res.status}). ${t || ''}`.trim();
        dispatch('error', { message: errorMessage });
      }
    } catch (e: any) {
      errorMessage = e?.message || 'Network error generating iteration';
      dispatch('error', { message: errorMessage });
    } finally {
      submitting = false;
      dispatch('finish');
    }
  }

  onDestroy(() => {
    stopVisualizer();
    clearStream();
  });
</script>

{#if open}
  <div class="modal-overlay" role="button" tabindex="0" on:click={close} on:keydown={(e) => (e.key==='Enter'||e.key===' ') && close()}></div>
  <div class="modal" role="dialog" aria-modal="true">
    <div class="modal-header">
      <h3>Iterate Narrative</h3>
    </div>
  <div class="modal-body">
      <div class="label">Formats (optional)</div>
      <div class="formats-list">
        {#each formats as f}
          <label class="fmt"><input type="checkbox" checked={format_ids.includes(f.id)} on:change={(e) => {
            const checked = (e.target as HTMLInputElement).checked;
            if (checked) {
              if (!format_ids.includes(f.id)) format_ids = [...format_ids, f.id];
            } else {
              format_ids = format_ids.filter((x) => x !== f.id);
            }
          }} /> {f.title}</label>
        {/each}
        {#if !formats.length}
          <div class="empty">No formats saved.</div>
        {/if}
      </div>
      <p class="hint">Add new input to refine the existing narrative. Choose one option below.</p>
      {#if selectedExcerpt}
        <div class="selection">
          <div class="title">Selected excerpt</div>
          <blockquote>{selectedExcerpt}</blockquote>
          <div class="row">
            <label class="mode">
              <input type="radio" name="scope" value="focus" checked={scope === 'focus'} on:change={() => (scope = 'focus')} />
              Refine whole narrative (focus on excerpt)
            </label>
            <label class="mode">
              <input type="radio" name="scope" value="section" checked={scope === 'section'} on:change={() => (scope = 'section')} />
              Rewrite only the selected part
            </label>
          </div>
        </div>
      {/if}

      <div class="modes">
        <label class="mode">
          <input type="radio" name="mode" value="note" checked={mode === 'note'} on:change={() => (mode = 'note')} />
          Use existing note
        </label>
        <label class="mode">
          <input type="radio" name="mode" value="text" checked={mode === 'text'} on:change={() => (mode = 'text')} />
          Type extra text
        </label>
        <label class="mode">
          <input type="radio" name="mode" value="record" checked={mode === 'record'} on:change={() => (mode = 'record')} />
          Record a quick note now
        </label>
      </div>

      {#if mode === 'note'}
        <div class="section">
          {#if loadingNotes}
            <div>Loading notes…</div>
          {:else}
            <label for="note">Select a note</label>
            <select id="note" bind:value={selectedNote}>
              <option value="" disabled>Select…</option>
              {#each notes as n}
                <option value={n.filename}>{n.title || n.filename}</option>
              {/each}
            </select>
          {/if}
        </div>
      {:else if mode === 'text'}
        <div class="section">
          <label for="extra">Extra text</label>
          <textarea id="extra" bind:value={extraText} placeholder="Add more context to guide the iteration"></textarea>
        </div>
      {:else}
        <div class="section">
          <div class="recording-controls">
            {#if !isRecording}
              <button class="btn primary" on:click={startRecording} disabled={uploading || polling}>Start recording</button>
            {:else}
              <button class="btn danger" on:click={stopRecording}>Stop recording</button>
            {/if}
            <div class={`recording-indicator ${isRecording ? 'live' : ''}`}>
              <span class="dot"></span>
              <span>{isRecording ? 'Recording…' : 'Standby'}</span>
            </div>
          </div>
          <div class={`waveform-panel ${isRecording ? 'active' : ''}`} bind:this={waveformContainer}>
            {#if mounted}
              <AudioWaveform
                peaks={waveformPeaks}
                position={1}
                height={WAVEFORM_HEIGHT}
                width={Math.max(120, waveformWidth)}
                color="#d1d5db"
                progressColor={isRecording ? '#ef4444' : '#6b7280'}
                barWidth={2}
              />
            {/if}
            <div class="waveform-overlay">
              <span>{isRecording ? 'We are listening. Speak freely.' : 'Press start to begin recording.'}</span>
            </div>
          </div>
          {#if uploading}
            <div class="status">Uploading…</div>
          {/if}
          {#if polling}
            <div class="status">Transcribing…</div>
          {/if}
          {#if pollError}
            <div class="error">{pollError}</div>
          {/if}
          {#if newNoteFilename}
            <div class="ok">Ready: {newNoteFilename}</div>
          {/if}
        </div>
      {/if}
    </div>
    <div class="modal-footer">
      <button class="btn" on:click={close} disabled={uploading || polling || isRecording || submitting}>Cancel</button>
      <button
        class="btn primary"
        on:click={submit}
        disabled={!canGenerate || uploading || polling || submitting}
      >{submitting ? 'Generating…' : 'Generate Iteration'}</button>
    </div>
    {#if errorMessage}
      <div class="error inline">{errorMessage}</div>
    {/if}
  </div>
{/if}

<style>
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 1100; }
  .modal { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
           background: #fff; padding: 1rem; border-radius: 8px; width: min(680px, 92vw); z-index: 1101; box-shadow: 0 10px 30px rgba(0,0,0,.2); }
  .modal-header { margin-bottom: .5rem; }
  .modal-body { display: flex; flex-direction: column; gap: .75rem; }
  .modes { display: flex; gap: 1rem; }
  .mode { display: flex; align-items: center; gap: .4rem; }
  .section { display: flex; flex-direction: column; gap: .5rem; }
  label { font-size: .9rem; color: #374151; }
  .label { font-size: .9rem; color: #374151; }
  select, textarea { padding: .5rem; border: 1px solid #e5e7eb; border-radius: 6px; }
  textarea { min-height: 120px; resize: vertical; }
  .modal-footer { display: flex; justify-content: flex-end; gap: .5rem; margin-top: .5rem; }
  .btn { border: none; padding: .5rem .9rem; border-radius: 6px; cursor: pointer; background: #e5e7eb; }
  .btn.primary { background: #3B82F6; color: white; }
  .btn.danger { background: #ef4444; color: #fff; }
  .btn[disabled] { opacity: .6; cursor: not-allowed; }
  .status { color: #374151; font-size: .9rem; }
  .error { color: #b91c1c; font-size: .9rem; }
  .error.inline { margin-top: .5rem; }
  .ok { color: #065f46; font-size: .9rem; }
  .recording-controls { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
  .recording-indicator { display: inline-flex; align-items: center; gap: .4rem; font-size: .9rem; color: #6b7280; transition: color .2s ease-in-out; }
  .recording-indicator .dot { width: .6rem; height: .6rem; border-radius: 999px; background: #9ca3af; display: inline-block; }
  .recording-indicator.live { color: #ef4444; font-weight: 500; }
  .recording-indicator.live .dot { background: #ef4444; box-shadow: 0 0 0 4px rgba(239,68,68,0.16); animation: pulse 1.5s ease-in-out infinite; }
  .waveform-panel { position: relative; width: 100%; min-height: 96px; background: #f9fafb; border: 1px dashed #d1d5db; border-radius: 8px; overflow: hidden; }
  .waveform-panel.active { border-style: solid; border-color: #ef4444; background: #fff4f4; }
  .waveform-overlay { position: absolute; inset: 0; display: flex; justify-content: center; align-items: center; pointer-events: none; font-size: .85rem; color: #6b7280; text-align: center; padding: 0 .75rem; }
  .waveform-panel.active .waveform-overlay { color: #b91c1c; font-weight: 500; }
  @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.3); } 70% { box-shadow: 0 0 0 10px rgba(239,68,68,0); } 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); } }
  .hint { color: #6b7280; margin: 0; }
  h3 { margin: 0; }
  .formats-list { display:flex; flex-direction: column; gap:.25rem; max-height: 180px; overflow:auto; border:1px solid #e5e7eb; border-radius:6px; padding:.5rem; }
  .fmt { display:flex; align-items:center; gap:.4rem; font-size:.95rem; }
  .empty { color:#6b7280; font-size:.9rem; }
</style>
      {#if (selectedNarratives?.length || 0) > 0}
        <label class="mode">
          <input type="radio" name="mode" value="narratives" checked={mode === 'narratives'} on:change={() => (mode = 'narratives')} />
          Use selected narratives ({selectedNarratives.length})
        </label>
      {/if}
