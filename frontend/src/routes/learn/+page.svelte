<script>
  import ScenarioDisplay from '$lib/components/ScenarioDisplay.svelte';
</script>

<svelte:head>
  <title>Learn - Narrative Hero</title>
</svelte:head>

<div class="learn-page-container">
  <h1>A Moment in Tokyo</h1>
  <ScenarioDisplay />
</div>

<style>
  .learn-page-container {
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  h1 {
    margin-bottom: 20px;
    color: #333;
  }
</style>