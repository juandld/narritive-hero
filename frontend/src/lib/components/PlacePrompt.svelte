<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let detectedPlace: string;

  const dispatch = createEventDispatcher();

  function handleYes() {
    dispatch('response', true);
  }

  function handleNo() {
    dispatch('response', false);
  }
</script>

<div
  style="margin-top: 1rem; padding: 1rem; background-color: #e6f7ff; border: 1px solid #91d5ff; border-radius: 8px; text-align: center;"
>
  <p>Detected your location: {detectedPlace}. Do you want to add this to the note?</p>
  <button
    on:click={handleYes}
    style="background-color: #52c41a; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;"
    >Yes</button
  >
  <button
    on:click={handleNo}
    style="background-color: #f5222d; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer;"
    >No</button
  >
</div>
