import { writable } from 'svelte/store';
import scenarios from '$lib/test/scenarios.json';

function createStoryStore() {
  const { subscribe, set, update } = writable(scenarios[0]);

  return {
    subscribe,
    // Function to advance the story to a specific scenario ID
    goToScenario: (id) => {
      const nextScenario = scenarios.find(s => s.id === id);
      if (nextScenario) {
        set(nextScenario);
      } else {
        console.error(`Scenario with id ${id} not found.`);
      }
    },
    // Reset to the beginning
    reset: () => set(scenarios[0])
  };
}

export const storyStore = createStoryStore();
