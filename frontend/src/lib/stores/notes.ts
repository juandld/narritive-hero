import { writable } from 'svelte/store';
import type { Note } from '$lib/types';
import { api } from '$lib/api';

export const notes = writable<Note[]>([]);
export const selectedNotes = writable<Set<string>>(new Set());

export const notesActions = {
  async refresh() {
    notes.set(await api.getNotes());
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

