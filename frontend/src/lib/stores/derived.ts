import { derived } from 'svelte/store';
import { notes } from '$lib/stores/notes';
import { selectedFolder } from '$lib/stores/folders';
import { filters } from '$lib/stores/filters';
import { computedDurations } from '$lib/stores/durations';
import { applyFilters } from '$lib/filters';

export const filteredNotes = derived(
  [notes, filters, selectedFolder, computedDurations],
  ([$notes, $filters, $selectedFolder, $durations]) => applyFilters($notes as any, $filters as any, $selectedFolder as string, $durations as Record<string, number>)
);
