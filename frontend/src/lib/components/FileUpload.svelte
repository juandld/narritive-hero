<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  let isDragover = false;

  function handleFileSelect(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      dispatch('file-selected', target.files[0]);
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragover = false;
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      dispatch('file-selected', e.dataTransfer.files[0]);
    }
  }
</script>

<div
  class:dragover={isDragover}
  on:dragenter={() => (isDragover = true)}
  on:dragleave={() => (isDragover = false)}
  on:dragover|preventDefault
  on:drop={handleDrop}
  style="border: 2px dashed #ccc; padding: 2rem; text-align: center; margin-bottom: 2rem;"
>
  <p>Drag and drop an audio file here, or click to select one.</p>
  <input type="file" accept="audio/*" on:change={handleFileSelect} style="display: none;" id="file-upload" />
  <label for="file-upload" style="background-color: #4285f4; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px;">
    Select Audio File
  </label>
</div>

<style>
  .dragover {
    background-color: #e6f7ff;
  }
</style>
