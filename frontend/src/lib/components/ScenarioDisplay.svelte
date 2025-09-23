<script>
  import { storyStore } from '$lib/storyStore.js';
  import { onMount } from 'svelte';

  let audioPlayer; // Bind to the audio element
  let isRecording = false;
  let mediaRecorder;
  let audioChunks = [];
  let audioBlob = null;

  // Reactive statement to play audio whenever the scenario changes
  $: if ($storyStore.audio_to_play_url && audioPlayer) {
    // A small delay can help ensure the new src is loaded before playing
    setTimeout(() => {
      audioPlayer.play().catch(e => console.error("Audio play failed:", e));
    }, 100);
  }

  async function toggleRecording() {
    if (isRecording) {
      // Stop recording
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
      isRecording = false;
    } else {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = event => {
          audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          audioChunks = [];
          
          const formData = new FormData();
          formData.append('audio_file', audioBlob, 'recording.webm');
          formData.append('current_scenario_id', $storyStore.id);

          try {
            const response = await fetch('http://localhost:8000/narrative/interaction', {
              method: 'POST',
              body: formData
            });

            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.nextScenario) {
              storyStore.goToScenario(result.nextScenario.id);
            } else {
              console.error("API Error:", result.error);
              alert("I'm sorry, I didn't quite catch that. Could you try again?");
            }
          } catch (error) {
            console.error("Error sending audio to backend:", error);
            alert("There was an issue connecting to the server. Please try again.");
          }
        };

        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;

      } catch (err) {
        console.error("Error accessing microphone:", err);
        alert("Microphone access is required to proceed. Please allow access and try again.");
      }
    }
  }

  // Handle browser autoplay restrictions
  function handleFirstInteraction() {
    if (audioPlayer && audioPlayer.paused) {
      audioPlayer.play().catch(e => {});
    }
    window.removeEventListener('click', handleFirstInteraction);
  }

  onMount(() => {
    if ($storyStore.audio_to_play_url) {
        audioPlayer.src = $storyStore.audio_to_play_url;
    }
    window.addEventListener('click', handleFirstInteraction);
  });

</script>

<!-- The actual audio element, hidden from the user -->
<audio bind:this={audioPlayer}></audio>

<div class="scenario-container">
  {#if $storyStore.image_url}
    <img src={$storyStore.image_url} alt="Scenario" class="scenario-image" />
  {/if}

  <div class="dialogue-box">
    <p class="character-dialogue-jp">{$storyStore.character_dialogue_jp}</p>
    <p class="character-dialogue-en"><em>{$storyStore.character_dialogue_en}</em></p>
  </div>

  {#if $storyStore.description}
    <p class="user-prompt">{$storyStore.description}</p>
  {/if}

  <div class="controls">
    <button 
      class="record-button" 
      class:isRecording 
      on:click={toggleRecording}
      aria-label={isRecording ? 'Stop Recording' : 'Start Recording'}
    >
      <svg viewBox="0 0 24 24" width="24" height="24" fill="white">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.49 6-3.31 6-6.72h-1.7z"/>
      </svg>
    </button>
  </div>

  <!-- For now, we'll include clickable text options to test the story flow -->
  <div class="debug-options">
    {#each $storyStore.options as option}
      <button on:click={() => storyStore.goToScenario(option.next_scenario)}>
        {option.text}
      </button>
    {/each}
  </div>

</div>

<style>
  .scenario-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    max-width: 600px;
    margin: auto;
    font-family: sans-serif;
    text-align: center;
  }
  .scenario-image {
    width: 100%;
    height: auto;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }
  .dialogue-box {
    background-color: #f0f0f0;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 20px;
    width: 100%;
  }
  .character-dialogue-jp {
    font-size: 1.5rem;
    font-weight: bold;
    margin: 0;
  }
  .character-dialogue-en {
    font-size: 1rem;
    color: #555;
    margin: 5px 0 0 0;
  }
  .user-prompt {
    font-size: 1.2rem;
    font-weight: 500;
    margin-bottom: 20px;
  }
  .controls {
    margin-bottom: 20px;
  }
  .record-button {
    background-color: #e63946;
    border: none;
    border-radius: 50%;
    width: 64px;
    height: 64px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    transition: background-color 0.2s, transform 0.2s;
  }
  .record-button:hover {
    background-color: #d62828;
  }
  .record-button.isRecording {
    background-color: #a8202a;
    transform: scale(0.95);
  }
  .debug-options button {
    margin: 0 5px;
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid #ccc;
    cursor: pointer;
  }
</style>