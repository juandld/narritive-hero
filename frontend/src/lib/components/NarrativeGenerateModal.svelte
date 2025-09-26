<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let open: boolean = false;
  export let selected: string[] = [];
  export let loading: boolean = false;

  const dispatch = createEventDispatcher();

  let extra_text = '';
  let provider: 'auto' | 'gemini' | 'openai' = 'auto';
  let model = '';
  let temperature = 0.2;

  function close() {
    if (loading) return;
    dispatch('close');
  }

  async function submit() {
    if (loading) return;
    dispatch('generate', { extra_text, provider, model: model.trim(), temperature });
  }
</script>

{#if open}
  <div class="modal-overlay" role="button" tabindex="0" on:click={close} on:keydown={(e) => (e.key==='Enter'||e.key===' ') && close()}></div>
  <div class="modal" role="dialog" aria-modal="true">
    <div class="modal-header">
      <h3>Create Narrative</h3>
      {#if loading}
        <div class="spinner" aria-label="Generating…" aria-busy="true"></div>
      {/if}
    </div>
    <div class="modal-body">
      <p style="margin:0 0 .5rem 0; color:#6b7280;">{selected.length} note(s) selected</p>
      <label>Extra Context</label>
      <textarea bind:value={extra_text} placeholder="Paste additional context to include (optional)"></textarea>

      <div class="row">
        <div class="col">
          <label>Provider</label>
          <select bind:value={provider}>
            <option value="auto">Auto (Gemini → OpenAI)</option>
            <option value="gemini">Gemini</option>
            <option value="openai">OpenAI</option>
          </select>
        </div>
        <div class="col">
          <label>Model (optional)</label>
          <input type="text" bind:value={model} placeholder="e.g., gemini-2.5-flash or gpt-4o" />
        </div>
      </div>

      <div class="row">
        <div class="col">
          <label>Temperature: {temperature.toFixed(2)}</label>
          <input type="range" min="0" max="1" step="0.05" bind:value={temperature} />
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" on:click={close} disabled={loading}>Cancel</button>
      <button class="btn primary" on:click={submit} disabled={loading}>{loading ? 'Generating…' : 'Generate'}</button>
    </div>
  </div>
{/if}

<style>
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 40; }
  .modal { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
           background: #fff; padding: 1rem; border-radius: 8px; width: min(640px, 92vw); z-index: 41; box-shadow: 0 10px 30px rgba(0,0,0,.2); }
  .modal-header { margin-bottom: .5rem; }
  .modal-header { display: flex; align-items: center; justify-content: space-between; }
  .modal-body { display: flex; flex-direction: column; gap: .75rem; }
  label { font-size: .9rem; color: #374151; }
  textarea { min-height: 120px; resize: vertical; padding: .5rem; border: 1px solid #e5e7eb; border-radius: 6px; }
  input[type="text"], select { padding: .5rem; border: 1px solid #e5e7eb; border-radius: 6px; width: 100%; }
  .row { display: flex; gap: .75rem; }
  .col { flex: 1; }
  .modal-footer { display: flex; justify-content: flex-end; gap: .5rem; margin-top: .5rem; }
  .btn { border: none; padding: .5rem .9rem; border-radius: 6px; cursor: pointer; background: #e5e7eb; }
  .btn.primary { background: #3B82F6; color: white; }
  .btn[disabled] { opacity: .6; cursor: not-allowed; }

  .spinner { width: 18px; height: 18px; border: 2px solid #93c5fd; border-top-color: #1d4ed8; border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
