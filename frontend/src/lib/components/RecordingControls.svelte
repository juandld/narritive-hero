<script lang="ts">
  export let isRecording: boolean;
  export let includeDate: boolean;
  export let includePlace: boolean;
  export let startRecording: () => void;
  export let stopRecording: () => void;
</script>

<div style="margin-bottom: 2rem; text-align: center;">
  <div style="margin-bottom: 1rem; display: flex; align-items: center; justify-content: center;">
    <input type="checkbox" bind:checked={includeDate} id="includeDate" style="margin-right: 10px;" />
    <label for="includeDate">Include Date</label>
  </div>
  <div style="margin-bottom: 1rem; display: flex; align-items: center; justify-content: center;">
    <input type="checkbox" bind:checked={includePlace} id="includePlace" style="margin-right: 10px;" />
    <label for="includePlace">Include Place</label>
  </div>
  {#if isRecording}
    <button
      on:click={stopRecording}
      style="background-color: #db4437; color: white; padding: 1rem 2rem; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer;"
    >
      Stop Recording
    </button>
  {:else}
    <button
      on:click={startRecording}
      style="background-color: #4285f4; color: white; padding: 1rem 2rem; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer;"
    >
      Start Recording
    </button>
  {/if}
</div>
