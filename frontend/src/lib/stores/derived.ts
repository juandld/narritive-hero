import { derived } from 'svelte/store';
import { notes } from '$lib/stores/notes';
import { selectedFolder } from '$lib/stores/folders';
import { filters } from '$lib/stores/filters';
import { computedDurations } from '$lib/stores/durations';
import { applyFilters } from '$lib/filters';

export const filteredNotes = derived(
  [notes, filters, selectedFolder, computedDurations],
  ([$notes, $filters, $selectedFolder, $durations]: [import('$lib/types').Note[], import('$lib/stores/filters').Filters, string, Record<string, number>]) =>
    applyFilters($notes, $filters, $selectedFolder, $durations)
);
