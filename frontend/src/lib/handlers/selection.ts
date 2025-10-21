import { get } from 'svelte/store';
import { filteredNotes } from '$lib/stores/derived';
import { selectedNotes } from '$lib/stores/notes';
import { writable } from 'svelte/store';

export const lastSelectedIndex = writable<number | null>(null);

export function onSelect(e: CustomEvent<{ filename: string; selected: boolean; index: number; shift?: boolean }>) {
  const { selected, index, shift } = e.detail || {} as any;
  const list = get(filteredNotes);
  const applyRange = (idx: number, state: boolean) => {
    const fn = list[idx]?.filename;
    if (!fn) return;
    selectedNotes.update((set) => {
      const ns = new Set(set);
      if (state) ns.add(fn); else ns.delete(fn);
      return ns;
    });
  };
  const last = get(lastSelectedIndex);
  if (shift && last !== null && list.length > 0) {
    const start = Math.max(0, Math.min(last, index));
    const end = Math.min(list.length - 1, Math.max(last, index));
    for (let i = start; i <= end; i++) applyRange(i, selected);
  } else {
    applyRange(index, selected);
  }
  if (!shift) lastSelectedIndex.set(index);
}

