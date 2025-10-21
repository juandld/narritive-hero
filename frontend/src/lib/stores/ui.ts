import { writable } from 'svelte/store';

export const expandedNotes = writable<Set<string>>(new Set());

export const uiActions = {
  toggleExpand(filename: string) {
    expandedNotes.update((set) => {
      const ns = new Set(set);
      if (ns.has(filename)) ns.delete(filename); else ns.add(filename);
      return ns;
    });
  },
};

