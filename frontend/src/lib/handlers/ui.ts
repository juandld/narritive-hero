import { includePlace, showPlacePrompt } from '$lib/stores/uiApp';

export function onPlacePromptResponse(e: CustomEvent<boolean>) {
  try {
    includePlace.set(!!e.detail);
  } finally {
    showPlacePrompt.set(false);
  }
}

