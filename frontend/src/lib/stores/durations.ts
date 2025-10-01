import { writable } from 'svelte/store';
export const computedDurations = writable<Record<string, number>>({});

