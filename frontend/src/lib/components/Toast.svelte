<script lang="ts">
  export let message: string;
  export let show: boolean;
</script>

{#if show}
  <div
    style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background-color: #333; color: white; padding: 1rem 2rem; border-radius: 8px; z-index: 1000; transition: opacity 0.5s ease;"
  >
    {message}
  </div>
{/if}
