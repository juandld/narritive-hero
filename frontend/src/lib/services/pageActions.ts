import { appActions } from '$lib/services/appActions';
import { notes as notesStore } from '$lib/stores/notes';
import { folders as foldersStore } from '$lib/stores/folders';
import { ensureDurations } from '$lib/services/durations';
import { computedDurations as durationsStore } from '$lib/stores/durations';

export async function refreshAll() {
  const { notes, folders } = await appActions.fetchNotesAndFolders();
  notesStore.set(notes);
  foldersStore.set(folders);
  // Compute missing durations and push into the durations store
  let map: Record<string, number> = {};
  const unsub = durationsStore.subscribe((v) => { map = v || {}; });
  if (typeof unsub === 'function') (unsub as any)();
  await ensureDurations(notes, map);
  durationsStore.set({ ...map });
}

export async function moveToFolder(folder: string, filenames: string[]) {
  await appActions.moveNotesToFolder(filenames, folder);
  await refreshAll();
}

export async function createFolder(name: string) {
  await appActions.createFolder(name);
  await refreshAll();
}

export async function createFolderAndMove(name: string, filenames: string[]) {
  await createFolder(name);
  await moveToFolder(name, filenames);
}

export async function deleteOne(filename: string) {
  await appActions.deleteNote(filename);
  await refreshAll();
}

export async function deleteMany(filenames: string[]) {
  await Promise.allSettled(filenames.map((f) => appActions.deleteNote(f)));
  await refreshAll();
}
