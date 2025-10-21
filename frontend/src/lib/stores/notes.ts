import { writable } from 'svelte/store';
import type { Note } from '$lib/types';
import { api } from '$lib/api';

export const notes = writable<Note[]>([]);
export const selectedNotes = writable<Set<string>>(new Set());

export const notesActions = {
  async refresh() {
    try {
      notes.set(await api.getNotes());
    } catch (error) {
      console.error('Failed to refresh notes:', error);
    }
  },
  toggleSelect(filename: string, on?: boolean) {
    selectedNotes.update((s) => {
      const ns = new Set(s);
      const next = on ?? !ns.has(filename);
      if (next) ns.add(filename); else ns.delete(filename);
      return ns;
    });
  },
  clearSelection() { selectedNotes.set(new Set()); },
};
