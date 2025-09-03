<script lang="ts">
  import RecordingControls from '../../lib/components/RecordingControls.svelte';

  let scenarios = [
    { id: 1, title: 'Ordering in a Restaurant', description: 'Practice ordering food and drinks in a restaurant setting.' },
    { id: 2, title: 'Asking for Directions', description: 'Learn how to ask for and understand directions.' },
    { id: 3, title: 'Shopping at a Market', description: 'Practice buying items and bargaining at a local market.' },
  ];

  let selectedScenario: any = null;
  let isRecording = false;

  function selectScenario(scenario: any) {
    selectedScenario = scenario;
  }

  function startRecording() {
    // Placeholder for recording logic
    isRecording = true;
  }

  function stopRecording() {
    // Placeholder for recording logic
    isRecording = false;
  }
</script>

<main style="font-family: sans-serif; max-width: 800px; margin: auto; padding: 2rem;">
  <h1 style="text-align: center; margin-bottom: 2rem;">Language Learning Scenarios</h1>

  {#if !selectedScenario}
    <div class="scenario-grid">
      {#each scenarios as scenario}
        <div class="scenario-card" on:click={() => selectScenario(scenario)}>
          <h2>{scenario.title}</h2>
          <p>{scenario.description}</p>
        </div>
      {/each}
    </div>
  {:else}
    <div>
      <button on:click={() => selectedScenario = null}>&larr; Back to Scenarios</button>
      <h2 style="margin-top: 2rem;">{selectedScenario.title}</h2>
      <p>{selectedScenario.description}</p>
      
      <div style="margin-top: 2rem;">
        <p>Your prompt will appear here. For now, just practice your response.</p>
      </div>

      <RecordingControls
        bind:isRecording
        includeDate={false}
        includePlace={false}
        {startRecording}
        {stopRecording}
      />
    </div>
  {/if}
</main>

<style>
  .scenario-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
  }

  .scenario-card {
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 1rem;
    cursor: pointer;
    transition: box-shadow 0.2s;
  }

  .scenario-card:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  }
</style>
